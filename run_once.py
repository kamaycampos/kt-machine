#!/usr/bin/env python3
"""One scheduling pass. Publishes whatever is due, then exits.

WHY THIS EXISTS. 13 Sept 2026. The machine ran on Railway, which bills for a
service that is awake 24 hours a day so it can be useful for the few seconds a
day something is actually due. Kamay's bill reached $13.79 against a $15 cap
with an estimate of $28.16, and he was clear: "im already paying you 20$ a
month, that already its my limit."

GitHub Actions is free without limit on a public repository - verified, not
assumed - so the same work costs nothing if it runs as a cron job instead of a
daemon. That is the whole change: `while True` becomes one pass, and the state
that lived on a Railway volume is committed back to the repository.

The media moves too. Instagram's API will not take bytes; it fetches from a
URL, which is why a server was needed at all. GitHub Releases serve public
files for free, so a release asset replaces the Railway media route.

WHAT IS DELIBERATELY UNCHANGED: every posting rule, the spacing, the source
mixing, the keyword freezing, the fence between the two accounts. All of that
is hard-won and lives in engine/. This file only decides when it runs and where
the files are.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "engine"))

STATE = os.path.join(HERE, "state", "manifest.json")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    # BEFORE the import, not after. engine/main.py reads KT_DATA at module level
    # and creates the directory as it loads, so setting the attribute afterwards
    # is too late - on a runner it tries to mkdir /data and dies read-only.
    os.environ.setdefault("KT_DATA", os.path.join(HERE, "state"))
    os.environ["KT_MEDIA_REMOTE"] = "1"      # videos are release assets, not files
    os.makedirs(os.path.join(HERE, "state"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "media"), exist_ok=True)

    import main as engine                                   # noqa: E402
    import poster                                           # noqa: E402

    # Point the engine at the repository instead of a Railway volume.
    engine.MANIFEST = STATE
    engine.MEDIA = os.path.join(HERE, "media")

    # And at GitHub Releases instead of the Railway media route. Release assets
    # have no folders, so a clip's path becomes its filename with a separator
    # that survives a URL untouched.
    owner = os.environ["GH_REPO"]                # e.g. kamaycampos/kt-machine
    tag = os.environ.get("MEDIA_TAG", "media")

    def media_url(rel):
        return (f"https://github.com/{owner}/releases/download/{tag}/"
                + rel.replace("/", "--"))
    engine.media_url = media_url

    man = engine.load()
    if not man.get("clips"):
        log("no clips in state - nothing to do")
        return 0

    changed = engine.plan(man)
    if changed:
        log(f"scheduled {changed} clip(s)")

    idxs, moved = engine.due_clips(man)
    if moved:
        log(f"pushed {moved} clip(s) past the spacing gap")
    if not idxs:
        engine.save(man)
        log("nothing due this run")
        return 0

    for i in idxs:
        man["clips"][i]["posting"] = True
    engine.save(man)

    for i in idxs:
        clip = dict(engine.load()["clips"][i])
        path = os.path.join(engine.MEDIA, clip["file"])
        if not os.path.exists(path):
            # The bytes live in the release, not the repository. Fetch just the
            # one file that is about to be posted; a checkout carrying three
            # gigabytes of video on every run would be its own kind of waste.
            log(f"fetching {clip['file']}")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            import urllib.request
            try:
                urllib.request.urlretrieve(media_url(clip["file"]), path)
            except Exception as e:
                log(f"  could not fetch: {e}")
                continue
        result, links = poster.publish(
            clip, path, media_url(clip["file"]), only=clip.get("retry_only"))
        m2 = engine.load()
        engine.record(m2, i, result, links)
        engine.save(m2)
        log(f"{clip['file']}: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
