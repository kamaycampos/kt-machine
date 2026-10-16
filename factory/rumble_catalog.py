"""Kevin's full episode catalog from Rumble -> factory/rumble_catalog.json.

19 Sept 2026. YouTube blocks cloud downloads; Kamay found that Kevin uploads
every episode to Rumble too ("The Kevin Trudeau Show Limitless",
rumble.com/c/TheKevinTrudeauOfficial). Each channel page carries the episode data as
embedded JSON: url, title, duration, upload date, height, is_short. Rumble sits
behind Cloudflare, so this poses as Chrome (curl_cffi) and retries.

    python factory/rumble_catalog.py
"""
import html, json, os, re, sys, time

# THE ADDRESS IS rumble.com/c/TheKevinTrudeauOfficial (Kamay confirmed it again 5 Oct
# 2026). On 30 Sept it briefly answered 404 and the catalogue froze at 632; it works.
# Since 5 Oct this runs at the start of every factory run (factory.yml, stock job), so
# a new upload enters the catalogue the day it appears - before, it ran only by hand,
# and nothing Kevin posted after 30 Sept could be stocked. A refused crawl changes
# nothing: the catalogue on disk is kept as it was.

# OUR OWN queue.py WAS SHADOWING PYTHON'S. 30 Sept 2026: this crawler died with
# "IndexError" inside factory/queue.py - because Python puts a script's own
# folder first on the import path, so `import queue` (which curl_cffi needs)
# found OUR file instead of the standard library's. Drop this folder from the
# path before anything else imports.
sys.path[:] = [q for q in sys.path
               if os.path.abspath(q or ".") != os.path.dirname(os.path.abspath(__file__))]

CHANNEL = "https://rumble.com/c/TheKevinTrudeauOfficial/videos?page={}"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rumble_catalog.json")


def get(url):
    """The channel page, or "" if every route is refused.

    14 Oct 2026: from GitHub's servers the page came back with no videos on every
    run since 7 Oct ("page 1: 0") while the same request from the Mac read all 639 -
    Cloudflare treats datacenter addresses differently. Kevin's 14 Oct upload was
    invisible for that reason alone. So: several browser fingerprints, and the log says which worked."""
    try:
        from curl_cffi import requests as cr
        fetchers = [(f"curl_cffi/{imp}", (lambda imp=imp: cr.get(url, impersonate=imp, timeout=30)))
                    for imp in ("chrome", "safari", "edge", "chrome120", "firefox")]
    except ImportError:
        import urllib.request
        ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
        fetchers = [("urllib", lambda: type("R", (), {"status_code": 200, "text": urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": ua}), timeout=30).read().decode("utf-8", "replace")}))]
    for attempt in range(2):
        for name, fetch in fetchers:
            try:
                r = fetch()
                if r.status_code == 200 and '"object_type":"video"' in r.text:
                    if attempt or name != fetchers[0][0]:
                        print(f"  (page read via {name})")
                    return r.text
                print(f"  {name}: HTTP {r.status_code}, {len(r.text)} bytes, no video data")
            except Exception as e:
                print(f"  {name}: {type(e).__name__}")
            time.sleep(2)
        time.sleep(10)
    return ""


def parse(html, page):
    out = {}
    for chunk in html.split('{"object_type":"video"')[1:]:
        g = lambda rx: (re.search(rx, chunk) or [None, None])[1]
        url = g(r'"url":"(https://rumble\.com/v[a-z0-9]+-[^"]+\.html)"')
        if not url:
            continue
        title = g(r'"title":"((?:[^"\\]|\\.)*)","duration"') or g(r'"title":"((?:[^"\\]|\\.)*)"') or ""
        out[url] = {"title": json.loads(f'"{title}"'), "dur": int(g(r'"duration":(\d+)') or 0),
                    "date": (g(r'"upload_date":"([^"]+)"') or "")[:10],
                    "height": int(g(r'"video_height":(\d+)') or 0),
                    "short": g(r'"is_short":(true|false)') == "true", "page": page,
                    # The direct stream: fetching it skips the episode's web page,
                    # which is the request Cloudflare refuses most often.
                    "hls": g(r'^,"videos":\[\{"url":"([^"]+)"')}
    return out


EMBED = "https://rumble.com/embedJS/u3/?request={}&ver=2&v={}"
CHANNEL_ID = "/c/TheKevinTrudeauOfficial"


def _json(url):
    # Plain and honest: these player endpoints answer GitHub's servers to a plain request,
    # while the Chrome disguise gets the same 403 the channel page gives (probe, 16 Oct).
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "kt-factory/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace"))


def discover(cat, budget=120):
    """The cloud route: Kevin's new uploads found through Rumble's embed player.

    16 Oct 2026: the channel page and every video page answer GitHub's servers with
    Cloudflare's 403, but the player's own endpoints (oEmbed, embedJS video + related,
    the hls stream) answer them 200. The related list of an episode carries the
    channel's NEXT upload: 7 Oct's list had 14 Oct's episode first. So walk forward
    from the newest episodes we know, keep only Kevin's channel (author checked on
    every video), and follow each new find in turn. Returns how many were added."""
    from urllib.parse import quote
    seeds = sorted((u for u, e in cat.items() if not e.get("short")),
                   key=lambda u: cat[u].get("date", ""), reverse=True)[:6]
    frontier, seen, added, calls = [], set(), 0, 0
    for u in seeds:
        v = cat[u].get("embed")
        if not v:
            try:
                calls += 1
                v = re.search(r"/embed/(v[0-9a-z]+)/", _json(
                    "https://rumble.com/api/Media/oembed.json?url=" + quote(u, safe=":/"))["html"])[1]
                cat[u]["embed"] = v
            except Exception as e:
                print(f"  oembed {u[-40:]}: {type(e).__name__}")
                continue
        frontier.append(v)
        seen.add(v)
    while frontier and calls < budget:
        v = frontier.pop(0)
        try:
            calls += 1
            rel = _json(EMBED.format("related", v)) or []
        except Exception as e:
            print(f"  related {v}: {type(e).__name__}")
            continue
        for r in rel:
            url = "https://rumble.com" + (r.get("l") or "").split("?")[0]
            if r.get("v") in seen or calls >= budget or not re.match(r"https://rumble\.com/v[a-z0-9]+-", url):
                continue
            seen.add(r["v"])
            if url in cat:
                cat[url].setdefault("embed", r["v"])
                continue
            try:
                calls += 1
                d = _json(EMBED.format("video", r["v"]))
            except Exception as e:
                print(f"  video {r['v']}: {type(e).__name__}")
                continue
            if not (d.get("author") or {}).get("url", "").endswith(CHANNEL_ID):
                continue
            w, h = int(d.get("w") or 0), int(d.get("h") or 0)
            cat[url] = {"title": html.unescape(d.get("title", "")), "dur": int(d.get("duration") or 0),
                        "date": (d.get("pubDate") or "")[:10], "height": min(w, h) if w and h else h,
                        "short": h > w, "page": 0, "embed": r["v"],
                        "hls": ((d.get("u") or {}).get("hls") or {}).get("url")}
            added += 1
            frontier.append(r["v"])
            print(f"  found via the player: {cat[url]['date']} {cat[url]['title'][:60]}")
        time.sleep(0.5)
    print(f"  player route: {added} new, {calls} requests")
    return added


def main():
    cat = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for p in range(1, 60):
        html = get(CHANNEL.format(p))
        got = parse(html, p) if html else {}
        print(f"page {p}: {len(got)}")
        if not got:
            break
        for u, e in got.items():
            cat.setdefault(u, {}).update(e)
    if p == 1:
        # Refused from this machine (GitHub's servers, since 7 Oct): the player route
        # finds the new uploads instead. Say so loudly only if that fails too.
        print("Rumble channel page refused from here - trying the player route")
        try:
            discover(cat)
        except Exception as e:
            print(f"::warning::player route failed too ({type(e).__name__}) - catalogue NOT refreshed")
    json.dump(cat, open(OUT, "w"), indent=1, ensure_ascii=False)
    full = [e for e in cat.values() if not e["short"] and e["dur"] >= 1200]
    print(f"{len(cat)} videos, {len(full)} full episodes, {sum(1 for e in full if e['height'] >= 1080)} at 1080p+")


if __name__ == "__main__":
    main()
