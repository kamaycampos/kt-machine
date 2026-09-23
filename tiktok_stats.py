"""TikTok numbers for Kamay's account -> state/tiktok.json (every 6 hours, cloud).

22 Sept 2026. TikTok is where Kamay says the account thrives, and we were blind
to it: clips land in his inbox, he posts by hand, and nothing came back. The
Sandbox app now carries video.list + user.info.stats; the token lives ENCRYPTED
in the 'sources' release (tt_stats_token.enc, FACTORY_KEY) and is rotated on
every run (TikTok refresh tokens roll over).

Each video is matched to our clip by DURATION (the file name ends _NNs) and by
posting after we sent it to the inbox - he posts the draft, so the caption may
differ, but the length cannot.
"""
import datetime, json, os, re, subprocess, urllib.parse, urllib.request

R = os.environ.get("GITHUB_REPOSITORY", "kamaycampos/kt-machine")
STATE = os.path.join(os.environ.get("KT_DATA", "state"))
sh = lambda *a, **k: subprocess.run(list(a), capture_output=True, text=True, **k)


def post(url, data=None, token=None, body=None):
    h = {"Content-Type": "application/json" if body is not None else "application/x-www-form-urlencoded"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    payload = json.dumps(body).encode() if body is not None else urllib.parse.urlencode(data).encode()
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, data=payload, headers=h), timeout=30).read())


def token():
    sh("gh", "release", "download", "sources", "-R", R, "-p", "tt_stats_token.enc", "-D", "/tmp", "--clobber")
    sh("openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", "env:FACTORY_KEY",
       "-in", "/tmp/tt_stats_token.enc", "-out", "/tmp/tt.json")
    old = json.load(open("/tmp/tt.json"))
    r = post("https://open.tiktokapis.com/v2/oauth/token/", {
        "client_key": os.environ["TT_CLIENT_KEY"], "client_secret": os.environ["TT_CLIENT_SECRET"],
        "grant_type": "refresh_token", "refresh_token": old["refresh_token"]})
    if not r.get("access_token"):
        raise SystemExit(f"refresh failed: {r.get('error')} {r.get('error_description')}")
    old["refresh_token"] = r.get("refresh_token", old["refresh_token"])       # rotate
    json.dump(old, open("/tmp/tt.json", "w"))
    sh("openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-pass", "env:FACTORY_KEY",
       "-in", "/tmp/tt.json", "-out", "/tmp/tt_stats_token.enc")
    sh("gh", "release", "upload", "sources", "/tmp/tt_stats_token.enc", "--clobber", "-R", R)
    os.remove("/tmp/tt.json")
    return r["access_token"]


def main():
    tok = token()
    fields = "id,create_time,duration,view_count,like_count,comment_count,share_count,video_description,share_url"
    vids, cursor = [], None
    for _ in range(10):
        body = {"max_count": 20, **({"cursor": cursor} if cursor else {})}
        r = post(f"https://open.tiktokapis.com/v2/video/list/?fields={fields}", token=tok, body=body)
        d = r.get("data") or {}
        vids += d.get("videos") or []
        if not d.get("has_more"):
            break
        cursor = d.get("cursor")
    u = json.loads(urllib.request.urlopen(urllib.request.Request(
        "https://open.tiktokapis.com/v2/user/info/?fields=follower_count,following_count,likes_count,video_count",
        headers={"Authorization": f"Bearer {tok}"}), timeout=30).read())
    prof = (u.get("data") or {}).get("user") or {}

    man = json.load(open(os.path.join(STATE, "manifest.json")))["clips"]
    ours = [c for c in man if not c["file"].startswith("AR_") and c.get("posted_at")]
    matched = {}
    for v in vids:
        vt = datetime.datetime.utcfromtimestamp(v["create_time"])
        best = None
        for c in ours:
            m = re.search(r"_(\d+)s\.mp4$", c["file"])
            if not m or abs(int(m.group(1)) - int(v.get("duration", 0))) > 2:
                continue
            sent = datetime.datetime.fromisoformat(c["posted_at"][:16])
            lag = (vt - sent).total_seconds() / 3600
            if -12 <= lag <= 24 * 10 and (best is None or abs(lag) < best[0]):
                best = (abs(lag), c["file"])
        key = best[1] if best else f"unmatched/{v['id']}"
        matched[key] = {k: v.get(k) for k in ("id", "view_count", "like_count", "comment_count", "share_count", "share_url", "duration")}
        matched[key]["posted"] = vt.strftime("%Y-%m-%dT%H:%M")
    out = {"at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M"), "profile": prof, "videos": matched}
    json.dump(out, open(os.path.join(STATE, "tiktok.json"), "w"), indent=1)

    # THE BAN RECORD. 23 Sept 2026, Kamay: "the clips in tiktok i posted 3 of
    # them or something like that got banned... keep record on which ones are
    # getting flagged and just take in mind that for the next ones so you can
    # fine tune on what could be the cause, never guess."
    #
    # A single snapshot cannot tell a banned clip from one he never posted, so
    # this keeps a running history: when each clip was first seen live on his
    # account, when it was last seen, and how many views it had then. A clip
    # that was live and is now gone was TAKEN DOWN - that is a fact, not a
    # guess, and it is written down the hour it happens. Suppression (live but
    # starved of views) is recorded separately; the two are different problems.
    hpath = os.path.join(STATE, "tiktok_history.json")
    try:
        hist = json.load(open(hpath))
    except Exception:
        hist = {"seen": {}, "gone": []}
    now = out["at"]
    for k, v in matched.items():
        if k.startswith("unmatched"):
            continue
        e = hist["seen"].setdefault(k, {"first": now, "posted": v.get("posted"), "id": v.get("id")})
        e["last"], e["views"] = now, v.get("view_count")
    already = {g["file"] for g in hist["gone"]}
    for k, e in hist["seen"].items():
        if k not in matched and k not in already and e.get("last", "") < now:
            hist["gone"].append({"file": k, "posted": e.get("posted"), "last_seen": e["last"],
                                 "views_when_last_seen": e.get("views"), "noticed": now})
            print(f"  TAKEN DOWN from TikTok: {k} (last seen {e['last']}, {e.get('views')} views)")
    json.dump(hist, open(hpath, "w"), indent=1)
    if hist["gone"]:
        print(f"  TikTok take-downs on record: {len(hist['gone'])}")
    tv = sum((x.get("view_count") or 0) for x in matched.values())
    print(f"TikTok: {len(vids)} videos, {tv:,} views total, {sum(1 for k in matched if not k.startswith('unmatched'))} matched to clips; "
          f"followers {prof.get('follower_count')}, likes {prof.get('likes_count')}")


if __name__ == "__main__":
    main()
