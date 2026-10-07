import json
import ssl
import sys
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from render_nginx import render


def run():
    host = sys.argv[1] if len(sys.argv) > 1 else "noticeboard.test"
    config = render(host)
    certdir = Path("/etc/letsencrypt/live") / host
    certdir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost", "-keyout", str(certdir / "privkey.pem"), "-out", str(certdir / "fullchain.pem")], check=True, capture_output=True)
    Path("/etc/nginx/sites-enabled/default").unlink(missing_ok=True)
    Path("/etc/nginx/conf.d/noticeboard.conf").write_text(config)
    subprocess.run(["nginx", "-t"], check=True)
    api = subprocess.Popen(["python", "-m", "uvicorn", "main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000", "--root-path", "/backend", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1"])
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen("http://127.0.0.1:8000/api/me", timeout=1)
            except urllib.error.HTTPError as exc:
                if exc.code == 401: break
            except OSError:
                pass
            time.sleep(.1)
        else:
            raise RuntimeError("API did not start")
        subprocess.run(["nginx"], check=True)
        context = ssl.create_default_context(cafile=str(certdir / "fullchain.pem"))
        for path, expected, content in [("/",200,"text/html"),("/app/plans",200,"text/html"),("/backend/api/me",401,"application/json"),("/backend/docs",404,"application/json"),("/backend/openapi.json",404,"application/json"),("/backend/not-a-route",404,"application/json")]:
            try:
                response=urllib.request.urlopen("https://localhost"+path,context=context)
            except urllib.error.HTTPError as error:
                response=error
            with response:
                assert response.status == expected, (path,response.status)
                assert content in response.headers["Content-Type"], path
                assert response.headers["Content-Security-Policy"], path
                assert response.headers["Strict-Transport-Security"], path
                assert response.headers["Cache-Control"] == "no-store", path
                if "json" in content:json.load(response)
                print("PASS",path,expected,flush=True)
        print("Verified Linux dependencies, real Nginx TLS, built React SPA, FastAPI proxy and production docs restrictions.",flush=True)
    finally:
        api.terminate()
        api.wait(timeout=10)


if __name__ == "__main__":
    run()
