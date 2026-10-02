#!/bin/bash
# Publish the member template to its own repo. The no-leak check runs first;
# a failed check publishes nothing. Usage: bash kit/publish_kit.sh <git-remote-url> [version]
set -euo pipefail
REMOTE="$1"; VER="${2:-$(python3 -c 'import json;print(json.load(open("kit/member/KIT.json"))["version"])')}"
OUT="$(mktemp -d)/affiliate-factory"
python3 kit/build_kit.py "$OUT" --check
cd "$OUT"
git init -q -b main
git add -A
git -c user.name="affiliate-factory" -c user.email="noreply@github.com" commit -q -m "The Affiliate Factory $VER"
git remote add origin "$REMOTE"
git push -q -u origin main
echo "published $VER -> $REMOTE"
