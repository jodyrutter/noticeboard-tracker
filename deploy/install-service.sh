#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
id noticeboard >/dev/null 2>&1 || { echo "Create the noticeboard service user first (see deploy/README.md)." >&2; exit 1; }
sudo -u noticeboard test -r "$repo_dir/backend/main.py" || {
    echo "The noticeboard user cannot read $repo_dir/backend/main.py. Grant traversal of the checkout's parent directories (see deploy/README.md)." >&2
    exit 1
}
unit_file=$(mktemp)
trap 'rm -f -- "$unit_file"' EXIT
python3.12 "$repo_dir/deploy/render_service.py" "$repo_dir" > "$unit_file"
sudo install -m 644 "$unit_file" /etc/systemd/system/noticeboard.service
sudo systemctl daemon-reload
sudo systemctl enable noticeboard
echo "Installed service for $repo_dir. Next: bash $repo_dir/deploy/update.sh"
