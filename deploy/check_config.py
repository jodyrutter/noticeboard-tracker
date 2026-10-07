import os
import sys


def validate(environ):
    errors = []
    for name in ("PG_HOST", "PG_DATABASE", "PG_USER", "PG_PASSWORD", "NOTICEBOARD_JWT_SECRET"):
        value = environ.get(name, "")
        if not value or "REPLACE_ME" in value or value.endswith("example.com"):
            errors.append(f"Set {name} in /etc/noticeboard/backend.env")
    if len(environ.get("NOTICEBOARD_JWT_SECRET", "").encode()) < 32:
        errors.append("NOTICEBOARD_JWT_SECRET must contain at least 32 bytes")
    if environ.get("PG_SSLMODE") != "verify-full" and environ.get("PG_HOST") not in ("127.0.0.1", "::1", "localhost"):
        errors.append("Remote PostgreSQL requires PG_SSLMODE=verify-full")
    if environ.get("PG_SSLMODE") == "verify-full" and not os.path.isfile(environ.get("PGSSLROOTCERT", "")):
        errors.append("PGSSLROOTCERT must point to a readable PostgreSQL CA certificate file")
    return errors


if __name__ == "__main__":
    errors = validate(os.environ)
    if errors:
        print("Deployment configuration failed:\n" + "\n".join(errors), file=sys.stderr)
        sys.exit(1)
