#!/usr/bin/env bash
set -euo pipefail
cd /opt/noticeboard-tracker
if [ "$(id -u)" -eq 0 ]; then
    echo "Run as the repository owner, not root; sudo is used only for installation/restart." >&2
    exit 1
fi
exec 9>.deploy.lock
flock -n 9 || { echo "Another deployment is running" >&2; exit 1; }
test -f /etc/systemd/system/noticeboard.service
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-production.txt
(cd frontend && npm ci && VITE_API_URL=/backend npm run build)
release="$(date -u +%Y%m%dT%H%M%SZ)-$(git rev-parse --short HEAD)-$$"
sudo install -d -m 755 "/var/www/noticeboard/releases/$release"
sudo cp -R frontend/dist/. "/var/www/noticeboard/releases/$release/"
sudo find "/var/www/noticeboard/releases/$release" -type d -exec chmod 755 {} +
sudo find "/var/www/noticeboard/releases/$release" -type f -exec chmod 644 {} +
sudo systemctl restart noticeboard
ready=false
for attempt in {1..20}; do
    code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/me || true)
    if [ "$code" = "401" ]; then ready=true; break; fi
    sleep 1
done
if [ "$ready" != true ]; then
    echo "API did not start; frontend release not activated. Check sudo journalctl -u noticeboard." >&2
    exit 1
fi
sudo ln -sfnT "/var/www/noticeboard/releases/$release" /var/www/noticeboard/current.next
sudo mv -Tf /var/www/noticeboard/current.next /var/www/noticeboard/current
echo "Release $release activated. Run the HTTPS smoke test and signed-in acceptance checks."
