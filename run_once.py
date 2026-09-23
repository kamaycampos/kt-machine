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


# THE POSTED LOG - 22 Sept 2026, and it is the reason a clip went out twice.
#
# Kamay: "the last clip for tiktok it got posted twice in ig". It did:
# NINE-TO-FIVE-BILLIONAIRE published at 17:28 and again at 20:28. The first run
# posted it perfectly and then FAILED TO SAVE that fact - its `git push` was
# rejected because another commit had landed while it was uploading, and
# nothing retried. The clip came back looking unposted, so the next run posted
# it again on every account.
#
# Git cannot be the only record of something that already happened in the
# world. This log is appended in the release the moment a clip is published -
# one API call, no merge, no rebase - and read at the start of every run, so a
# lost commit can no longer cause a second post.
LOG_ASSET = "posted_log.txt"


def tiktok_failed(status):
    """True when TikTok did not take the clip. Only two answers mean it did:
    it reached the inbox, or TikTok is still processing an upload it accepted."""
    s = (status or "").lower()
    if not s:
        return False
    return not ("inbox" in s or "processing" in s)


def _repo():
    return os.environ.get("GH_REPO", "kamaycampos/kt-machine")


def posted_log():
    import urllib.request
    url = f"https://github.com/{_repo()}/releases/download/state/{LOG_ASSET}"
    try:
        body = urllib.request.urlopen(url, timeout=30).read().decode()
    except Exception as e:
        log(f"posted log unreadable ({e}) - treating as empty")
        return {}
    out = {}
    for line in body.splitlines():
        if "|" in line:
            f, at = line.split("|", 1)
            out[f.strip()] = at.strip()
    return out


def posted_log_add(rel, when):
    import subprocess
    known = posted_log()
    if rel in known:
        return
    known[rel] = when
    body = "\n".join(f"{f}|{t}" for f, t in sorted(known.items())) + "\n"
    path = os.path.join("/tmp", LOG_ASSET)
    open(path, "w").write(body)
    r = subprocess.run(["gh", "release", "upload", "state", path, "--clobber", "-R", _repo()],
                       capture_output=True, text=True)
    if r.returncode:
        log(f"  COULD NOT WRITE THE POSTED LOG: {r.stderr.strip()[-160:]}")


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

    # DRY RUN. Railway is still live during the changeover, and two schedulers
    # both seeing a clip as due would publish it twice - the duplicate-post
    # failure this project has already paid for. So the new machine proves it
    # can read the state, resolve credentials and reach the media BEFORE it is
    # ever allowed to publish anything.
    dry = os.environ.get("DRY_RUN") == "1"

    man = engine.load()
    if not man.get("clips"):
        log("no clips in state - nothing to do")
        return 0

    # WHAT THE WORLD SAYS IS ALREADY POSTED WINS OVER WHAT THE FILE SAYS.
    already = posted_log()
    recovered = 0
    for c in man["clips"]:
        at = already.get(c["file"])
        if at and not c.get("posted_at") and not c.get("done"):
            c["posted_at"] = at
            c["status"] = dict(c.get("status") or {}, recovered="published; the state commit was lost")
            c.pop("posting", None); c.pop("posting_at", None)
            recovered += 1
            log(f"already published, not posting again: {c['file']} ({at})")
    if recovered:
        engine.save(man)

    # TIKTOK FAILS ON ITS OWN AND USED TO STAY FAILED.
    #
    # 22 Sept 2026, Kamay: "send me a new one so i can post in tiktok". The
    # 23:16 clip reached Instagram, Facebook and YouTube and TikTok answered
    # "chunk 1/1 failed 500" - their server, not ours. Nothing retried, so his
    # inbox stayed empty and the clip was marked posted and never looked at
    # again. A platform that fails alone is now retried alone, on the next run,
    # without republishing anywhere else.
    if not dry:
        for c in man["clips"]:
            # `done` means the clip finished its posting life, which is true of
            # EVERY clip that could need this - the first version of this guard
            # skipped exactly the set it was written for. What must never be
            # retried is a clip that was retired before it ever published.
            if not c.get("tiktok_retry") or not c.get("posted_at"):
                continue
            if c.get("tiktok_tries", 0) >= 3:
                c.pop("tiktok_retry", None)
                log(f"tiktok gave up after 3 tries: {c['file']}")
                engine.save(man)
                continue
            path = os.path.join(engine.MEDIA, c["file"])
            if not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                import urllib.request
                try:
                    urllib.request.urlretrieve(media_url(c["file"]), path)
                except Exception as e:
                    log(f"tiktok retry - could not fetch {c['file']}: {e}")
                    continue
            res, _l = poster.publish(c, path, media_url(c["file"]), only=["tiktok"])
            tt = (res or {}).get("tiktok", "")
            log(f"tiktok retry {c['file']}: {tt}")
            st = dict(c.get("status") or {}); st["tiktok"] = tt; c["status"] = st
            c["tiktok_tries"] = c.get("tiktok_tries", 0) + 1
            c["tiktok_retry"] = tiktok_failed(tt)
            if not c["tiktok_retry"]:
                c.pop("tiktok_retry", None)
            engine.save(man)
            break                      # one retry per run; never a burst

    # RELEASE A LOCK NOBODY IS HOLDING.
    #
    # 14 Sept 2026, Kamay: "today felt like it was less posting". It was: three
    # posts instead of five, and his queue was empty behind them. Two clips -
    # KT_MED/13 and KT_RICH/05 - were carrying posting=True with an empty status
    # and no posted_at, one of them since 8 September.
    #
    # The flag is set just before publishing and cleared by record(). A run that
    # dies in between - a timed-out upload, a cancelled job, a runner killed
    # mid-step - leaves it set, and due_clips() then skips that clip FOREVER.
    # Nothing reports it. The clip is simply never posted again and the day
    # quietly gets shorter, which is exactly what he noticed.
    #
    # A lock is only meaningful while the run holding it is alive. This one is
    # stamped, and anything older than an hour is assumed dead - the job itself
    # times out at 25 minutes, so an hour cannot be a live run.
    freed = 0
    for c in man["clips"]:
        if not c.get("posting") or c.get("posted_at"):
            continue
        t = c.get("posting_at")
        if t and (time.time() - t) < 3600:
            continue                      # a live run really is holding it
        c.pop("posting", None)
        c.pop("posting_at", None)
        c.pop("stale", None)
        c.pop("scheduled_at", None)       # that slot is long past; re-plan it
        freed += 1
        log(f"released a dead posting lock: {c['file']}")
    if freed:
        engine.save(man)

    changed = engine.plan(man)
    if changed:
        log(f"scheduled {changed} clip(s)")

    idxs, moved = engine.due_clips(man)
    if dry:
        import urllib.request
        log(f"DRY RUN - would publish {len(idxs)} clip(s)")
        missing = 0
        for c in man["clips"]:
            if c.get("posted_at") or c.get("done") or not c.get("scheduled_at"):
                continue
            u = media_url(c["file"])
            try:
                r = urllib.request.urlopen(urllib.request.Request(u, method="HEAD"),
                                           timeout=30)
                ok = r.status == 200
            except Exception:
                ok = False
            if not ok:
                missing += 1
                log(f"  MEDIA MISSING: {c['file']}")
        log(f"credentials visible: " + ", ".join(
            k for k in ("IG_ACCESS_TOKEN", "FB_ACCESS_TOKEN", "YT_REFRESH_TOKEN",
                        "TT_REFRESH_TOKEN", "AR_IG_ACCESS_TOKEN")
            if os.environ.get(k)))
        log(f"scheduled clips whose media is unreachable: {missing}")
        for i in idxs:
            log(f"  would post now: {man['clips'][i]['file']}")
        return 1 if missing else 0
    if moved:
        log(f"pushed {moved} clip(s) past the spacing gap")
    if not idxs:
        engine.save(man)
        log("nothing due this run")
        return 0

    for i in idxs:
        man["clips"][i]["posting"] = True
        man["clips"][i]["posting_at"] = int(time.time())
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
        if any(v == "posted" for v in (result or {}).values()):
            posted_log_add(clip["file"], time.strftime("%Y-%m-%dT%H:%M"))
        m2 = engine.load()
        engine.record(m2, i, result, links)
        if tiktok_failed((result or {}).get("tiktok", "")):
            m2["clips"][i]["tiktok_retry"] = True
            log(f"  tiktok will be retried next run: {(result or {}).get('tiktok')}")
        engine.save(m2)
        log(f"{clip['file']}: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
