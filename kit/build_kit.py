#!/usr/bin/env python3
"""Build the member template - THE AFFILIATE FACTORY - from this live machine.

WHY THE KIT IS GENERATED, NOT COPIED BY HAND.
The Connector's law 5: one copy of everything. kt-machine is the machine that is
proven on a real account (214,805 views on one reel, 6 posts a day, no server).
The member kit is the same machine with Kamay's account taken out - his plans,
his state, his secrets, Yaren's Awakened Rise lane. If the kit were a hand-made
copy it would drift on the first fix. Generated, every improvement made here
reaches every member on the next build.

    python3 kit/build_kit.py OUT_DIR          # writes the template to OUT_DIR
    python3 kit/build_kit.py OUT_DIR --check  # build, then verify nothing private leaked

What it does:
  1. copies every tracked file EXCEPT what belongs to one account (EXCLUDE)
  2. resets the records (state, plans, series, source list) to empty
  3. replaces this repo's name with a placeholder that the member's Claude
     fills in on day one (kit/member/personalize.py)
  4. lays the member files (CLAUDE.md, START_HERE.md, ...) over the top
  5. switches posting OFF by default: a new member is in STUDIO mode (clips and
     captions made, posted by hand) until they set the repo variable AUTOPOST=on
"""
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMBER = os.path.join(ROOT, "kit", "member")
PLACEHOLDER = "YOUR-GITHUB-NAME/YOUR-REPO"
PAGES_PLACEHOLDER = "YOUR-GITHUB-NAME.github.io/YOUR-REPO"

# Belongs to Kamay's or Yaren's account, or to the kit's own build - never shipped.
EXCLUDE = [
    r"^state/",                       # his record of every clip and post
    r"^docs/",                        # his public board
    r"^factory/plans/",               # his clip choices
    r"^factory/reports/",
    r"^factory/AR_PLANNING\.md$",     # Yaren's lane
    r"^factory/ar_source_plan\.json$",
    r"^factory/kt_series\.json$",
    r"^factory/source_plan\.json$",
    r"^connector/",
    r"^kit/",                         # the builder itself and Dustin's brief
]

# Records reset to empty, in the exact shape the engine reads.
EMPTY = {
    "state/manifest.json": {"clips": []},
    "state/metrics.json": [],
    "state/tiktok.json": {"at": None, "profile": {}, "videos": {}},
    "state/tiktok_history.json": {"seen": {}, "gone": []},
    "factory/kt_series.json": {},
    "factory/plans/_done.json": [],
    "factory/source_plan.json": {
        "note": "Your month's episodes. Your Claude fills this in (append only).",
        "episodes": []},
    "docs/thumbs.json": {},
    "state/dms.json": {"sent": {}, "seen": {}, "errors": []},
}

# Text a member's copy must not carry. --check fails the build on any of these.
PRIVATE = ["kamaycampos", "AR_IG_", "theawakenedrise", "links.fans/wealthfrequency"]
# The one place a member's copy may name us: where its updates come from.
UPSTREAM = "kamaycampos/affiliate-factory"
# ...except where they are inert history in code comments of engine files.
PRIVATE_OK_IN = (".py",)


def tracked():
    out = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True,
                         text=True, check=True).stdout.split("\n")
    return [f for f in out if f and not any(re.search(p, f) for p in EXCLUDE)]


def rewrite(text):
    text = text.replace("links.fans/wealthfrequency", "your-affiliate-link")
    text = text.replace("kamaycampos00@gmail.com", "YOUR-EMAIL")
    text = text.replace("kamaycampos.github.io/kt-machine", PAGES_PLACEHOLDER)
    text = text.replace("kamaycampos/kt-machine", PLACEHOLDER)
    return text


def studio_by_default(path):
    """Posting is opt-in for a member. DRY_RUN unless vars.AUTOPOST == 'on'."""
    s = open(path).read()
    s = re.sub(r"KT_TZ: *\"?America/New_York\"?", "KT_TZ: ${{ vars.KT_TZ || 'America/New_York' }}", s)
    s = s.replace("DRY_RUN: ${{ inputs.dry_run && '1' || '0' }}",
                  "DRY_RUN: ${{ (inputs.dry_run || vars.AUTOPOST != 'on') && '1' || '0' }}")
    # Comment -> DM runs on every pass, just before the board and panel are rebuilt.
    s = s.replace("      - name: Rebuild the calendar and the captions board\n", """      - name: Comment keyword -> DM with the link
        if: ${{ !inputs.dry_run && inputs.trial == '' }}
        continue-on-error: true          # a DM pass must never block a post
        env:
          DM_AUTO: ${{ vars.DM_AUTO }}
          DM_TEXT: ${{ vars.DM_TEXT }}
          OFFER_URL: ${{ secrets.OFFER_URL }}
          KT_CTA_KEYWORDS: ${{ secrets.KT_CTA_KEYWORDS }}
          IG_USER_ID: ${{ secrets.IG_USER_ID }}
          IG_ACCESS_TOKEN: ${{ secrets.IG_ACCESS_TOKEN }}
          FB_PAGE_ID: ${{ secrets.FB_PAGE_ID }}
          FB_ACCESS_TOKEN: ${{ secrets.FB_ACCESS_TOKEN }}
        run: python dm/dm_reply.py

      - name: Rebuild the calendar and the captions board
""")
    s = s.replace("git add state/manifest.json state/metrics.json docs",
                  "git add state/manifest.json state/metrics.json state/dms.json docs")
    # The member's control panel is written right after the captions board.
    s = s.replace("run: python build_pages.py", "run: python build_pages.py && python panel/build_panel.py")
    # Awakened Rise's credentials are Yaren's account - a member has one account.
    s = re.sub(r"(?m)^[ \t]+AR_[A-Z_]+: \$\{\{ secrets\.AR_[A-Z_]+ \}\}\n", "", s)
    open(path, "w").write(s)


def build(out):
    if os.path.exists(out) and os.listdir(out):
        sys.exit(f"{out} is not empty - refusing to write over it")
    os.makedirs(out, exist_ok=True)
    for f in tracked():
        src, dst = os.path.join(ROOT, f), os.path.join(out, f)
        os.makedirs(os.path.dirname(dst) or out, exist_ok=True)
        try:
            s = open(src, encoding="utf-8").read()
            open(dst, "w", encoding="utf-8").write(rewrite(s))
        except UnicodeDecodeError:          # fonts, models: copied as bytes
            shutil.copyfile(src, dst)
        shutil.copymode(src, dst)
    for f, v in EMPTY.items():
        p = os.path.join(out, f)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(v, open(p, "w"), indent=1)
    # The default offer link was Kamay's. A member's is a secret (OFFER_URL).
    p = os.path.join(out, "engine", "poster.py")
    s = open(p).read().replace('DEFAULT_OFFER = "https://links.fans/wealthfrequency"',
                               'DEFAULT_OFFER = ""  # set the OFFER_URL secret')
    open(p, "w").write(s)
    for wf in os.listdir(os.path.join(out, ".github", "workflows")):
        studio_by_default(os.path.join(out, ".github", "workflows", wf))
    # The member's own files go on top, at the root of their repo.
    for base, _, files in os.walk(MEMBER):
        for name in files:
            src = os.path.join(base, name)
            rel = os.path.relpath(src, MEMBER)
            dst = os.path.join(out, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    # The member's README is the front door, not Kamay's engine notes.
    shutil.move(os.path.join(out, "README.md"), os.path.join(out, "ENGINE.md"))
    shutil.copy2(os.path.join(MEMBER, "START_HERE.md"), os.path.join(out, "README.md"))
    rehash_shared(out)
    print(f"kit built: {out} ({sum(len(f) for _, _, f in os.walk(out))} files)")


def rehash_shared(root):
    """Re-hash shared/MANIFEST.json after the repo name is written into shared/.

    setup.sh refuses every factory run when a shared module's hash is wrong
    (30 Sept 2026: the factory sat dead for a day on exactly that). Writing the
    member's repo name into shared/kt_lock.py changes its hash, so the manifest
    is rewritten here, the moment the file changes."""
    import hashlib
    p = os.path.join(root, "shared", "MANIFEST.json")
    if not os.path.exists(p):
        return
    man = json.load(open(p))
    for f in man["files"]:
        man["files"][f] = hashlib.sha1(open(os.path.join(root, "shared", f), "rb").read()).hexdigest()
    json.dump(man, open(p, "w"), indent=1)
    open(p, "a").write("\n")


def check(out):
    bad = []
    for base, dirs, files in os.walk(out):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            p = os.path.join(base, name)
            try:
                s = open(p, encoding="utf-8").read()
            except UnicodeDecodeError:
                continue
            s = s.replace(UPSTREAM, "")
            for w in PRIVATE:
                if w in s and not (name.endswith(PRIVATE_OK_IN) and w == "AR_IG_"):
                    bad.append(f"{os.path.relpath(p, out)}: {w}")
    # The fence code still names AR_ in poster.py; that is inert with no AR_ secrets.
    if bad:
        print("PRIVATE TEXT IN THE KIT:\n  " + "\n  ".join(bad))
        return 1
    # Every python file still compiles after the rewrite.
    r = subprocess.run([sys.executable, "-m", "compileall", "-q", out],
                       capture_output=True, text=True)
    for base, dirs, _ in os.walk(out):          # leave no build litter behind
        for d in [d for d in dirs if d == "__pycache__"]:
            shutil.rmtree(os.path.join(base, d))
    if r.returncode:
        print(r.stdout + r.stderr)
        return 1
    import hashlib
    man = json.load(open(os.path.join(out, "shared", "MANIFEST.json")))["files"]
    drift = [f for f, h in man.items() if hashlib.sha1(
        open(os.path.join(out, "shared", f), "rb").read()).hexdigest() != h]
    if drift:
        print(f"shared engine drifted, setup.sh would refuse every run: {drift}")
        return 1
    print("check ok: nothing private, every module compiles, shared manifest true")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    build(sys.argv[1])
    if "--check" in sys.argv:
        sys.exit(check(sys.argv[1]))
