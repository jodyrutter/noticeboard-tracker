# EC2 deployment

Browser HTTPS -> Nginx -> React static files or /backend/* -> FastAPI at 127.0.0.1:8000.

The browser never contacts the HTTP backend directly. Production React always uses relative `/backend` URLs, ignoring VITE_API_URL overrides; local Vite development keeps its existing proxy. No permissive CORS policy is needed. Nginx strips `/backend/` on proxy requests; Uvicorn's root-path setting preserves that prefix in generated redirects. This follows [FastAPI's TLS termination model](https://fastapi.tiangolo.com/deployment/https/) and [Nginx proxy_pass URI replacement](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass).

These files target a Linux EC2 host using systemd and Nginx. Commands below use Ubuntu 24.04 package names. Confirm your EC2 OS before running package installation; Amazon Linux needs equivalent packages and may require SELinux policy for the proxy/static directory. This is a single-instance deployment, not an ALB/CloudFront configuration. Do not put another proxy in front without reviewing trusted client-IP handling.

## Your Ubuntu instance: 13.219.9.139

This is an IP address, so DNS/domain ownership is not required for the IP-certificate option. First confirm this is still your instance's public address and preferably associate an Elastic IP to keep it stable. If it changes, update the Nginx configuration and obtain a certificate for the new address. Run initial setup steps 2–5 below, then use these IP-specific certificate steps instead of step 6:

Use Certbot **5.4 or newer**; Ubuntu's apt package may be older. The Ubuntu snap installation is `sudo snap install --classic certbot` (use `sudo snap refresh certbot` if already installed). Confirm `/snap/bin/certbot --version`. Use that executable consistently rather than an older apt copy. Check the snap renewal timer is active.

```bash
cd ~/noticeboard
python3.12 deploy/render_nginx.py 13.219.9.139 --http-only | sudo tee /etc/nginx/conf.d/noticeboard.conf >/dev/null
sudo nginx -t
sudo systemctl reload nginx
sudo /snap/bin/certbot certonly --webroot -w /var/www/letsencrypt --preferred-profile shortlived --ip-address 13.219.9.139 --cert-name 13.219.9.139
python3.12 deploy/render_nginx.py 13.219.9.139 | sudo tee /etc/nginx/conf.d/noticeboard.conf >/dev/null
sudo nginx -t
sudo systemctl reload nginx
sudo install -d /etc/letsencrypt/renewal-hooks/deploy
sudo install -m 755 deploy/certbot-renew-hook.sh /etc/letsencrypt/renewal-hooks/deploy/noticeboard
sudo /snap/bin/certbot renew --dry-run
systemctl list-timers --all
python3.12 deploy/smoke.py https://13.219.9.139
```

Allow inbound port 80 for ACME validation and port 443 for the site; restrict SSH and keep 8000/5173 private. IP certificates expire after about six days: verify automatic renewal runs at least twice daily, reloads Nginx after renewal, and monitor failures. Do not rely on a one-time manual certificate. The supplied Nginx template installs the certificate explicitly; the Certbot Nginx installer is not needed. See [Let's Encrypt's IP certificate instructions](https://letsencrypt.org/2026/03/11/shorter-certs-certbot).

If PostgreSQL runs on this same EC2 instance, set PG_HOST=127.0.0.1 in backend.env. Browser requests will be `https://13.219.9.139/backend/...`; the separate backend connection remains private HTTP on loopback.

## Initial setup

1. Point a domain's DNS A record to the instance's Elastic IP. Only add an AAAA record if IPv6 is configured. Allow inbound 443 and 80 (certificate issuance/renewal and HTTPS redirect); restrict SSH to your administrative source. Do not expose 8000 or 5173. Restrict PostgreSQL 5432 to approved application/admin sources. If PostgreSQL is on this same instance, use 127.0.0.1, not its public IP.
2. Install Python 3.12, venv, Node.js 22 LTS with npm, Nginx, Certbot (5.4+ for IP certificates), Git and curl. On Ubuntu 24.04 the non-Node packages can be installed with `sudo apt-get update` and `sudo apt-get install python3.12-venv nginx git curl`. Install Node using your chosen trusted Node distribution; verify `node --version` and `npm --version`. Enable Nginx with `sudo systemctl enable --now nginx`.
3. Use your existing `~/noticeboard` checkout (or clone to a directory owned by your deployment/SSH user). The update script detects its checkout location. That user owns the checkout and .venv; the service account must not own/write the code. Give the service account read/traverse access to the checkout (normal 755 directories and 644 source files). Do not put secrets inside it. Create the service account and directories:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin noticeboard
sudo install -d -m 750 -o root -g noticeboard /etc/noticeboard
sudo install -d -m 755 /var/www/noticeboard/releases /var/www/letsencrypt
cd ~/noticeboard
sudo install -m 600 -o root -g root deploy/backend.env.example /etc/noticeboard/backend.env
sudoedit /etc/noticeboard/backend.env
```

Run useradd only if that account does not exist. Set real values in backend.env. It is a systemd EnvironmentFile, not a shell script: use NAME=value lines, no export or command substitution. Generate a secret using `python3.12 -c 'import secrets; print(secrets.token_urlsafe(48))'`, paste it into the file, and keep it stable across deployments. Do not commit it. Systemd reads the root-only file before dropping privileges.

For remote PostgreSQL, install the correct CA certificate at PGSSLROOTCERT with read access for noticeboard, and set PG_SSLMODE=verify-full with a matching PG_HOST certificate name. For a database strictly on loopback you can explicitly set PG_SSLMODE=disable if TLS is not configured and omit PGSSLROOTCERT. This only affects the local database connection, never browser HTTPS. The service startup check rejects remote non-verified TLS and unset/example secrets. One Uvicorn worker is configured, so memory rate limiting works per instance but resets on restart; use shared Redis before scaling.

4. Verify the existing DB schema/grants. This repository still lacks the earlier SQL baseline/migrations referenced in README. Preserve/export your actual schema and have the DB admin apply reviewed missing changes; the update script deliberately does not invent or automatically run migrations. A working current DB is required for login and business actions.
5. For your `/home/ubuntu/noticeboard` checkout, Ubuntu may prevent the service user from traversing `/home/ubuntu`. Grant that user traversal only, without making the home directory publicly readable:

```bash
sudo apt-get install acl
sudo setfacl -m u:noticeboard:--x /home/ubuntu
sudo -u noticeboard test -r /home/ubuntu/noticeboard/backend/main.py
```

The checkout itself must have normal readable files/traversable directories. Keep secrets in the root-only `/etc/noticeboard/backend.env`. `install-service.sh` checks source readability and renders WorkingDirectory and Python executable paths for the actual checkout. Its generated service uses ProtectHome=read-only so it can read the home-based checkout; filesystem writes remain prohibited by ProtectSystem=strict. Reinstall the service if you move the checkout. Do not install the static `/opt` example service directly for a home checkout.

Install the backend service and build/start the app:

```bash
bash deploy/install-service.sh
bash deploy/update.sh
```

6. Bootstrap certificate issuance. Replace `noticeboard.example.com` with your real domain in all commands; do not leave that example in place:

```bash
python3.12 deploy/render_nginx.py noticeboard.example.com --http-only | sudo tee /etc/nginx/conf.d/noticeboard.conf >/dev/null
sudo nginx -t
sudo systemctl reload nginx
sudo certbot certonly --webroot -w /var/www/letsencrypt -d noticeboard.example.com
python3.12 deploy/render_nginx.py noticeboard.example.com | sudo tee /etc/nginx/conf.d/noticeboard.conf >/dev/null
sudo nginx -t
sudo systemctl reload nginx
```

Bootstrap serves only the ACME challenge over HTTP; it does not expose the login screen without TLS. Ensure no other Nginx configuration already owns this domain. If `nginx -t` fails, fix it before reloading. The production template requires the issued certificate files and redirects ordinary HTTP traffic to HTTPS.

7. Enable/check the Certbot renewal timer provided by your distribution (`systemctl list-timers`), install a renewal deploy hook to run `systemctl reload nginx`, and run `sudo certbot renew --dry-run`. Certificates must renew automatically. Install the supplied hook with `sudo install -m 755 deploy/certbot-renew-hook.sh /etc/letsencrypt/renewal-hooks/deploy/noticeboard`.
8. Run `python3.12 deploy/smoke.py https://noticeboard.example.com`. Then sign in and exercise HR, Manager and Trainee actions against dedicated test records. The smoke test validates TLS using the system trust store, frontend deep links and the real API proxy, but intentionally does not create users or modify the DB.

## Subsequent updates

Commit/push the local changes first so EC2 can pull them. On EC2, as the checkout owner:

```bash
cd ~/noticeboard
git pull --ff-only
bash deploy/update.sh
python3.12 deploy/smoke.py https://13.219.9.139
```

The script installs pinned Python dependencies, runs npm ci, builds React, restarts FastAPI, checks its unauthenticated 401 response and activates the new static release. Secret settings stay in /etc/noticeboard. Changes to the service or Nginx templates require reinstall/render, syntax check, daemon-reload/reload as in setup. DB migrations require a separate reviewed operation and backup.

This is a small single-instance update with possible downtime, not a zero-downtime/atomic full-stack deployment. Dependency installation changes the shared .venv and a failed restart may leave the API unavailable; inspect `sudo journalctl -u noticeboard -n 100` and `sudo systemctl status noticeboard`. Old static releases are retained. For rollback, return the checkout to a known-good release, rerun update.sh and handle any DB migration compatibility separately. No automatic destructive DB rollback is attempted.

Nginx serves only frontend build files, never the repository or backend.env. CSP allows same-origin scripts/API calls and the existing Google Fonts styles/fonts. Inline styles are allowed because the existing charts use them. FastAPI public docs/OpenAPI are disabled by NOTICEBOARD_ENV=production. HSTS is enabled on this hostname only. Nginx overwrites forwarded-client headers; Uvicorn trusts only its loopback proxy. Do not expose the API port or broaden that trust to all sources.

## Local deployment verification

With Docker Desktop running, build frontend first, then from the repository root:

```bash
docker build -f deploy/Dockerfile.verify -t noticeboard-proxy-verify .
docker run --rm noticeboard-proxy-verify
```

This verification image is not the deployment runtime. It installs the pinned Linux/Python 3.12 dependencies and tests real Nginx with a temporary trusted test certificate, real FastAPI, built React deep links, protected API responses and production docs restrictions. No AWS connection or database is used. It does not verify systemd or your EC2 certificate/DB/firewall setup.

All deployment files, production dependency pins, production API URL restriction and docs setting are AI-written additions. Existing API handlers, ownership checks and React screens are reused.
