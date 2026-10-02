#!/usr/bin/env python3
"""Day one: make this copy of the Affiliate Factory YOURS.

Your Claude runs this for you during setup. It:
  1. writes your repository's name everywhere the machine needs it
  2. prints two random keys for your GitHub secrets (FACTORY_KEY, TRANSCRIPT_KEY)
  3. prints the exact clicks left for you to do

    python3 personalize.py                  # reads your repo name from git
    python3 personalize.py --repo you/name  # or say it
"""
import os
import re
import secrets
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLACEHOLDER = "YOUR-GITHUB-NAME/YOUR-REPO"
PAGES_PLACEHOLDER = "YOUR-GITHUB-NAME.github.io/YOUR-REPO"
SKIP_DIRS = {".git", "__pycache__"}


def repo_from_git():
    try:
        url = subprocess.run(["git", "-C", HERE, "remote", "get-url", "origin"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None
    m = re.search(r"github\.com[:/]+([^/]+/[^/.]+?)(?:\.git)?/?$", url)
    if not m:  # Claude Code on the web clones through a proxy: .../git/owner/repo
        m = re.search(r"/([^/]+/[^/.]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else None


def main():
    repo = sys.argv[sys.argv.index("--repo") + 1] if "--repo" in sys.argv else repo_from_git()
    if not repo or "/" not in repo:
        sys.exit("Could not tell your repository's name. Run: python3 personalize.py --repo YOURNAME/YOURREPO")
    owner, name = repo.split("/", 1)
    pages = f"{owner.lower()}.github.io/{name}"
    changed = 0
    for base, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            p = os.path.join(base, f)
            try:
                s = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, PermissionError):
                continue
            t = s.replace(PAGES_PLACEHOLDER, pages).replace(PLACEHOLDER, repo)
            if t != s:
                open(p, "w", encoding="utf-8").write(t)
                changed += 1
    print(f"Your machine now knows it is {repo} ({changed} files).")
    print()
    print("Two secrets to paste. Repo -> Settings -> Secrets and variables -> Actions -> New repository secret")
    print(f"  FACTORY_KEY      {secrets.token_urlsafe(32)}")
    print(f"  TRANSCRIPT_KEY   {secrets.token_urlsafe(32)}")
    print(f"  OFFER_URL        <your affiliate link>")
    print()
    print("Then: Settings -> Pages -> Deploy from a branch -> main, /docs -> Save")
    print(f"Your board will live at https://{pages}/")


if __name__ == "__main__":
    main()
