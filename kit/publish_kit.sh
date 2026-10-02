#!/bin/bash
# Publish the member template to its own repo. The no-leak check runs first;
# a failed check publishes nothing. Usage: bash kit/publish_kit.sh <git-remote-url> [version]
#
# ONE HISTORY, ALWAYS. Members bring updates in with `update`, which merges the
# template into their copy. That only works if every version is a new commit
# on the same history, so this clones what is published and commits on top -
# it never starts a fresh history and never force-pushes.
set -euo pipefail
REMOTE="$1"; VER="${2:-$(python3 -c 'import json;print(json.load(open("kit/member/KIT.json"))["version"])')}"
TMP="$(mktemp -d)"; OUT="$TMP/build"; REPO="$TMP/repo"
python3 kit/build_kit.py "$OUT" --check
git clone -q "$REMOTE" "$REPO"
cd "$REPO"
if git rev-parse -q --verify HEAD >/dev/null; then git rm -q -r --cached . >/dev/null; fi
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -a "$OUT"/. .
git add -A
if git diff --cached --quiet; then echo "nothing new to publish"; exit 0; fi
git -c user.name="affiliate-factory" -c user.email="noreply@github.com" commit -q -m "The Affiliate Factory $VER"
git push -q origin HEAD:main
echo "published $VER -> $REMOTE"
