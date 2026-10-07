import sys
import urllib.error
import urllib.request


def check(base):
    if not base.startswith("https://"):
        raise ValueError("Use the public HTTPS site URL")
    for path, status, content in (("/", 200, "text/html"), ("/app/plans", 200, "text/html"), ("/backend/api/me", 401, "application/json")):
        try:
            response = urllib.request.urlopen(base.rstrip("/") + path, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            assert response.status == status, (path, response.status)
            assert content in response.headers.get("Content-Type", ""), path
            assert response.headers.get("Strict-Transport-Security"), path
            assert response.headers.get("Content-Security-Policy"), path
            print(f"PASS {path}: {status}")
    print("HTTPS, SPA routing and API proxy passed. This does not test DB credentials or login.")


if __name__ == "__main__":
    check(sys.argv[1])
