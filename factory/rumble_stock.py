"""Stock the factory with HD episodes straight from Rumble - no Mac needed.

19 Sept 2026. The cloud can download Kevin's episodes from Rumble by posing as
Chrome (the first request is sometimes refused by Cloudflare; a retry passes).
Picks the newest full episodes at 1080p or better that were never clipped and
are not fenced to Yaren, downloads up to 1440p, encrypts them into the 'sources'
release (the repository is public), and adds them to sources_index.json so
transcribe.py and the clip plans can use them.

    python factory/rumble_stock.py [--max N] [--stock N]
"""
import json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
K = os.path.expanduser("~/Kamay")
SRC = os.path.join(K, "Kamay Content", "1_RAW", "KT_SOURCE")

# A NEW COPY RUNS BEFORE ITS KEYS EXIST (2 Oct 2026). "Use this template" starts
# the factory on the first push, before setup has added FACTORY_KEY. openssl
# would then encrypt with an EMPTY password and upload files the member's real
# key can never open. No key = nothing stocked, nothing uploaded, a clear note.
if __name__ == "__main__" and not os.environ.get("FACTORY_KEY"):   # run as a job, not imported
    print("::notice::FACTORY_KEY is not set yet - finish setup (say 'set me up' to your Claude). Nothing was stocked.")
    sys.exit(0)

TAG, REPO = "sources", os.environ.get("GITHUB_REPOSITORY", "kamaycampos/kt-machine")
arg = lambda n, d: int(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
MAX, STOCK = arg("--max", 2), arg("--stock", 6)
GIVE_UP = 3                     # failed runs before an unfetchable episode steps aside
PART = 1900 * 1024 * 1024       # GitHub refuses a release asset of 2 GiB or more


def sh(*a):
    return subprocess.run(list(a), capture_output=True, text=True)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def height(p):
    m = re.search(r"Video:.*?(\d{3,4})x(\d{3,4})", sh("ffmpeg", "-i", p).stderr)
    return int(m[2]) if m else 0


def plain_links(url, e):
    """Fresh direct file links for an episode, best first, from Rumble's player.

    20 Oct 2026. Ten episodes - five of them on Yaren's list - were given up after three
    runs: every try went through yt-dlp posing as Chrome, and the 16 Oct probe found that
    GitHub's servers get Cloudflare's 403 WITH the Chrome disguise while a plain request
    to the player and its file links answers 200. The same 1080p links download fine
    from the Mac. So when the disguised tries fail, ask the player (oEmbed -> embedJS)
    for its current file list and fetch the tallest one plainly."""
    import urllib.request
    from urllib.parse import quote
    J = lambda u: json.loads(urllib.request.urlopen(urllib.request.Request(
        u, headers={"User-Agent": "kt-factory/1.0"}), timeout=30).read().decode("utf-8", "replace"))
    out = []
    try:
        v = e.get("embed") or re.search(r"/embed/(v[0-9a-z]+)/", J(
            "https://rumble.com/api/Media/oembed.json?url=" + quote(url, safe=":/"))["html"])[1]
        d = J(f"https://rumble.com/embedJS/u3/?request=video&ver=2&v={v}")
        mp4s = ((d.get("ua") or {}).get("mp4") or {})
        out = [x["url"] for _h, x in sorted(mp4s.items(), key=lambda kv: -int(kv[0])) if x.get("url")][:1]
    except Exception as ex:
        print(f"    player: {type(ex).__name__}")
    if (e.get("hls") or "").endswith(".mp4") and e["hls"] not in out:
        out.append(e["hls"])
    return out


def main():
    sh("gh", "release", "download", TAG, "-R", REPO, "-p", "sources_index.json", "-D", "/tmp", "--clobber")
    idx = json.load(open("/tmp/sources_index.json")) if os.path.exists("/tmp/sources_index.json") else {}
    # Given up after GIVE_UP runs - unless it never had the plain route (plain_links):
    # those get their rounds again, once, and are marked "plain" when they fail.
    retry = lambda e: e.get("status") == "fetch_failed" and (e.get("fails", 0) < GIVE_UP
                                                             or not e.get("plain"))
    done = set(json.load(open(os.path.join(HERE, "plans", "_done.json"))))
    planned = " ".join(open(os.path.join(HERE, "plans", f)).read()
                       for f in os.listdir(os.path.join(HERE, "plans")) if f.endswith(".json"))
    # ONLY WHAT A PLANNER WILL PLAN COUNTS AS WAITING (14 Oct 2026). Every stocked episode
    # that was never planned counted here - dozens picked up automatically weeks ago that
    # neither month list names - so the stock looked full, nothing was fetched, five
    # episodes on Kamay's list were never downloaded and his queue ran dry for 27 hours.
    _lists = set()
    for _f in ("source_plan.json", "ar_source_plan.json"):
        if os.path.exists(os.path.join(HERE, _f)):
            _lists |= {x["id"] for x in json.load(open(os.path.join(HERE, _f)))["episodes"]}
    waiting = [v for v, e in idx.items() if e.get("status") == "stocked" and not e.get("test")
               and v not in planned and v in _lists]
    missing = [v for v in _lists if v not in idx or retry(idx[v])]
    need = min(MAX, max(STOCK - len(waiting), len(missing)))
    print(f"month lists: {len(_lists)} episodes, {len(missing)} not downloaded yet")
    series = json.load(open(os.path.join(HERE, "kt_series.json")))
    used = {norm(os.path.splitext(s.get("source", ""))[0])[:40] for s in series.values()}
    cat = json.load(open(os.path.join(HERE, "rumble_catalog.json")))
    # THE NEWEST UPLOAD IS NEVER KEPT WAITING (Kamay, 11 Oct 2026: the latest episode is
    # cut and posted the same day, priority #1). A full episode uploaded in the last 14
    # days that is not stocked yet is fetched even when the stock target is met, and it
    # goes ahead of the month lists below.
    _cut = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 14 * 86400))
    _vid = lambda u: (re.search(r"/(v[a-z0-9]+)-", u) or [None, ""])[1]
    fresh = {_vid(u) for u, e in cat.items()
             if not e["short"] and e.get("date", "") >= _cut and _vid(u) not in idx}
    if fresh and need <= 0:
        need = min(MAX, len(fresh))
    print(f"{len(waiting)} stocked episode(s) not yet planned; stock target {STOCK}; "
          f"{len(fresh)} new upload(s); fetching {max(need, 0)}")
    if need <= 0:
        return
    # A FAILED FETCH IS REMEMBERED (5 Oct 2026). Every run spent ~5 minutes on each of
    # five episodes whose saved stream was a signed CDN link that had expired
    # (hugh.cdn.rumble.cloud/....mp4 - 403) and whose page Cloudflare refuses, while
    # the rumble.com/hls-vod/ links kept working. They are retried on the next runs,
    # and after GIVE_UP failed runs they step aside so the slot goes to an episode
    # that can actually be fetched.
    have = {e.get("rumble") for e in idx.values() if not retry(e)}
    # AN EPISODE HE NAMED IS NEVER FILTERED OUT BY LENGTH. 30 Sept 2026: Kamay
    # put that day's upload at the top of the list - "You Keep Missing The
    # Biggest Opportunities", 4K, SIX MINUTES - and the stocker silently ignored
    # it, because the 20-minute floor exists to keep stray clips out of an
    # AUTOMATIC pick. A deliberate choice is not a stray clip. Listed episodes
    # need only be long enough to hold a clip; everything else still has to
    # clear the floor.
    listed = set()
    for f in ("source_plan.json", "ar_source_plan.json"):
        fp = os.path.join(HERE, f)
        if os.path.exists(fp):
            listed |= {x["id"] for x in json.load(open(fp))["episodes"]}
    vid_of = lambda u: (re.search(r"/(v[a-z0-9]+)-", u) or [None, ""])[1]
    floor = lambda u, e: 180 if vid_of(u) in listed or vid_of(u) in fresh else 1200
    pick = [(u, e) for u, e in sorted(cat.items(), key=lambda x: x[1]["date"], reverse=True)
            if not e["short"] and e["dur"] >= floor(u, e) and e["height"] >= 1080
            and u not in have and norm(e["title"])[:40] not in used]
    # THE MONTH'S LISTS COME FIRST - both of them, alternating, so neither
    # account waits behind the other: Kamay's money lane (source_plan.json) and
    # Yaren's hidden/esoteric lane (ar_source_plan.json). A source is still cut
    # for only one of them; that is kt_fence.py's job, not this one's.
    lists = []
    for f in ("source_plan.json", "ar_source_plan.json"):
        fp = os.path.join(HERE, f)
        if os.path.exists(fp):
            lists.append([e["id"] for e in json.load(open(fp))["episodes"]])
    if lists:
        order = [v for pair in __import__("itertools").zip_longest(*lists) for v in pair if v]
        rank = lambda ue: order.index(re.search(r"/(v[a-z0-9]+)-", ue[0])[1]) \
            if re.search(r"/(v[a-z0-9]+)-", ue[0])[1] in order else len(order)
        pick.sort(key=rank)
    # Within that order, an episode whose stream is a rumble.com/hls-vod/ playlist goes
    # before one carrying an old signed CDN file link (those expire and answer 403).
    pick.sort(key=lambda ue: 0 if "/hls-vod/" in (ue[1].get("hls") or "") else 1)
    pick.sort(key=lambda ue: 0 if _vid(ue[0]) in fresh else 1)      # newest uploads first, always
    stocked, tried = 0, 0
    for url, e in pick:
        if stocked >= need or tried >= need * 2:
            break
        tried += 1
        vid = re.search(r"/(v[a-z0-9]+)-", url)[1]
        mp4 = os.path.join(SRC, f"{vid}.mp4")
        print(f"  {vid}  {e['dur']/60:.0f} min  {e['height']}p  {e['title'][:70]}")
        for attempt in range(6):
            # Alternate: the direct stream (skips the page Cloudflare guards) and the page.
            target = e.get("hls") if (attempt % 2 == 0 and e.get("hls")) else url
            r = sh("yt-dlp", "--no-warnings", "-q", "--impersonate", "chrome", "-N", "8",
                   "-f", "bv*[height<=?2160]+ba/b[height<=?2160]", "--merge-output-format", "mp4",
                   "-o", mp4, target)
            if os.path.exists(mp4):
                break
            time.sleep(15 * (attempt + 1))
        if not os.path.exists(mp4):
            for link in plain_links(url, e):
                r = sh("curl", "-sSLf", "--retry", "3", "--retry-delay", "10", "-A", "kt-factory/1.0",
                       "-o", mp4, link)
                if r.returncode == 0 and height(mp4) > 0:
                    print("    fetched by the plain route (player file link)")
                    break
                if os.path.exists(mp4):
                    os.remove(mp4)
        h = height(mp4) if os.path.exists(mp4) else 0
        if h == 0:
            # Cloudflare turned every attempt away. Not the episode's fault: try
            # again on the next run instead of writing it off.
            prev = idx.get(vid, {})
            fails = prev.get("fails", 0) + 1 if prev.get("status") == "fetch_failed" else 1
            idx[vid] = {"title": e["title"], "rumble": url, "status": "fetch_failed", "fails": fails,
                        "plain": True}
            print(f"    NOT FETCHED ({fails}/{GIVE_UP}) ({r.stderr.strip()[-120:]})")
            continue
        # THE TOP RESOLUTION KEVIN UPLOADED, NOT THE FIRST ONE THAT ARRIVED (14 Oct 2026).
        # Six episodes came in below what Rumble offers - the 7 Oct one at 1440p while its
        # stream carries 3840x2160 - because a refused stream fell back to the page, which
        # can serve less. Kamay: "only deliver the best of the best quality". When the
        # file is short of the catalogue's height, fetch the stream again and keep the
        # better copy.
        want = int(e.get("height") or 0)
        if 0 < h < want and e.get("hls"):
            better = mp4[:-4] + ".hi.mp4"
            for attempt in range(3):
                sh("yt-dlp", "--no-warnings", "-q", "--impersonate", "chrome", "-N", "8",
                   "-f", "bv*[height<=?2160]+ba/b[height<=?2160]", "--merge-output-format", "mp4",
                   "-o", better, e["hls"])
                if os.path.exists(better) and height(better) > h:
                    os.replace(better, mp4)
                    print(f"    upgraded {h}p -> {height(mp4)}p (catalogue says {want}p)")
                    h = height(mp4)
                    break
                time.sleep(20 * (attempt + 1))
            if h < want:
                print(f"    NOTE: kept {h}p, Rumble lists {want}p - the stream refused a better copy")
        if h < 1080:
            print(f"    REFUSED: {h}p - under the 1080p gate")
            idx[vid] = {"title": e["title"], "rumble": url, "status": "rejected", "height": h}
            continue
        # OVER 2 GiB GOES UP IN PARTS (5 Oct 2026). GitHub refuses any release asset of
        # 2 GiB or more, and every episode over ~70 minutes encrypts past that: five of
        # ten downloads in one run were thrown away at upload ("size must be less than
        # 2147483648"), so nothing new reached the planners and both queues ran dry.
        # The ciphertext is cut into <vid>.mp4.enc.part00, part01, ... and
        # transcribe.fetch_source joins them back byte for byte before decrypting.
        # Streamed through split, so the disk holds the video once, not twice.
        enc = f"/tmp/{vid}.mp4.enc"
        if os.path.getsize(mp4) < PART - 1024 * 1024:
            sh("openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-pass", "env:FACTORY_KEY",
               "-in", mp4, "-out", enc)
            files = [enc]
        else:
            subprocess.run(f'openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:FACTORY_KEY -in "{mp4}" '
                           f'| split -b {PART} -d -a 2 - "{enc}.part"', shell=True, check=True)
            files = sorted(f"/tmp/{f}" for f in os.listdir("/tmp") if f.startswith(f"{vid}.mp4.enc.part"))
        u = None
        for f in files:
            u = sh("gh", "release", "upload", TAG, f, "--clobber", "-R", REPO)
            os.remove(f)
            if u.returncode:
                break
        # The download is in the release now (or failed); keep the runner's disk free
        # for the next one - ten long episodes do not fit on one runner at once.
        os.remove(mp4)
        if u.returncode:
            print(f"    UPLOAD FAILED {u.stderr[-150:]}")
            continue
        if len(files) > 1:
            print(f"    uploaded in {len(files)} parts")
        idx[vid] = {"title": e["title"], "rumble": url, "duration": e["dur"], "height": h,
                    "status": "stocked", "uploaded": time.strftime("%Y-%m-%dT%H:%M")}
        stocked += 1
        print(f"    STOCKED {h}p")
    json.dump(idx, open("/tmp/sources_index.json", "w"), indent=1)
    sh("gh", "release", "upload", TAG, "/tmp/sources_index.json", "--clobber", "-R", REPO)


if __name__ == "__main__":
    main()
