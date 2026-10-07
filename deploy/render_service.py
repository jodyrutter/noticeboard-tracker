import argparse
from pathlib import Path
import re


def render(repo):
    root = str(Path(repo).resolve())
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", root):
        raise ValueError("Checkout path must be an absolute Linux path without spaces or special characters")
    template = (Path(__file__).parent / "noticeboard.service").read_text()
    return template.replace("/opt/noticeboard-tracker", root).replace("ProtectHome=true", "ProtectHome=read-only")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo")
    args = parser.parse_args()
    print(render(args.repo))
