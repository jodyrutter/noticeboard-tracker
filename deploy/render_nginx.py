import argparse
import ipaddress
from pathlib import Path
import re


def render(domain, https=True):
    try:
        ipaddress.IPv4Address(domain)
        is_ipv4 = True
    except ValueError:
        is_ipv4 = False
    if not is_ipv4 and (len(domain) > 253 or not re.fullmatch(r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}", domain)):
        raise ValueError("Supply a DNS domain name or IPv4 address, without a scheme, port or path")
    directory = Path(__file__).resolve().parent
    text = (directory / "nginx-http.conf.template").read_text()
    if https:
        text += "\n" + (directory / "nginx-https.conf.template").read_text()
    return text.replace("__DOMAIN__", domain.lower())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("domain")
    parser.add_argument("--http-only", action="store_true")
    args = parser.parse_args()
    print(render(args.domain, not args.http_only))
