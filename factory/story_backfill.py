"""Give every clip already in the queue its story cut - in the cloud, Mac shut.

28 Sept 2026, Kamay: "i want you to make our IG to post EVERY SINGLE CLIP WE POST
to also posted in the story". The renderer now cuts a `__story.mp4` for every new
clip, but the ones already queued were rendered before that existed, and a story
is refused for anything over 60 seconds. This walks the queue, fetches each clip
that has no story cut yet, makes one, and uploads it beside the clip.

    python factory/story_backfill.py [--limit N] [--dry]

Nothing here touches the manifest: a story cut is an extra file, not a decision.
"""
import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.environ.get("GITHUB_REPOSITORY", "kamaycampos/kt-machine")
TAG = "media"
LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 40
DRY = "--dry" in sys.argv
sys.path.insert(0, os.path.expanduser("~/Kamay"))
import kt_render as R                                             # noqa: E402

url_for = lambda rel: f"https://github.com/{REPO}/releases/download/{TAG}/" + rel.replace("/", "--")


def have(rel, tries=1):
    """Is the story cut already in the release?

    28 Sept 2026: a release asset is not servable the instant the upload returns.
    Checking immediately reported four good files as "uploaded but not fetchable"
    - all four answered 200 a minute later. So the check after an upload waits."""
    import time
    for i in range(tries):
        try:
            req = urllib.request.Request(url_for(rel).replace(".mp4", "__story.mp4"), method="HEAD")
            if urllib.request.urlopen(req, timeout=30).status == 200:
                return True
        except Exception:
            pass
        if i + 1 < tries:
            time.sleep(8)
    return False


def main():
    man = json.load(open(os.path.join(ROOT, "state", "manifest.json")))["clips"]
    todo = [c for c in man if not c.get("done") and not c.get("posted_at")]
    print(f"{len(todo)} clip(s) waiting in the queue")
    made = skipped = 0
    for c in todo[:LIMIT]:
        rel = c["file"]
        if have(rel):
            skipped += 1
            continue
        work = os.path.join("/tmp", os.path.basename(rel))
        try:
            urllib.request.urlretrieve(url_for(rel), work)
        except Exception as e:
            print(f"  {rel}: cannot fetch ({e})")
            continue
        dur = R.duration_of(work)
        if dur <= 59.0:
            print(f"  {rel}: {dur:.0f}s - posts as its own story, nothing to cut")
            skipped += 1
            os.remove(work)
            continue
        if DRY:
            print(f"  {rel}: {dur:.0f}s - would cut a story")
            os.remove(work)
            continue
        out = R.make_story(work)
        if not out:
            print(f"  {rel}: story cut failed")
            os.remove(work)
            continue
        asset = rel.replace("/", "--").replace(".mp4", "__story.mp4")
        tmp = os.path.join("/tmp", asset)
        os.replace(out, tmp)
        r = subprocess.run(["gh", "release", "upload", TAG, tmp, "--clobber", "-R", REPO],
                           capture_output=True, text=True)
        os.remove(tmp)
        os.remove(work)
        if r.returncode:
            print(f"  {rel}: upload failed {r.stderr[-120:]}")
            continue
        # VERIFY THE ARTIFACT: the upload returning 0 is not the story existing.
        if not have(rel, tries=4):
            print(f"  {rel}: uploaded but not fetchable")
            continue
        made += 1
        print(f"  {rel}: story ready")
    print(f"\n{made} story cut(s) made, {skipped} already fine")


if __name__ == "__main__":
    main()
