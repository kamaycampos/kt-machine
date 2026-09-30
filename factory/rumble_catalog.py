"""Kevin's full episode catalog from Rumble -> factory/rumble_catalog.json.

19 Sept 2026. YouTube blocks cloud downloads; Kamay found that Kevin uploads
every episode to Rumble too ("The Kevin Trudeau Show Limitless",
rumble.com/c/TheKevinTrudeauOfficial). Each channel page carries the episode data as
embedded JSON: url, title, duration, upload date, height, is_short. Rumble sits
behind Cloudflare, so this poses as Chrome (curl_cffi) and retries.

    python factory/rumble_catalog.py
"""
import json, os, re, sys, time

# THE CHANNEL ADDRESS IS DEAD AS OF 30 SEPT 2026. rumble.com/c/TheKevinTrudeauOfficial
# answers 404 (Rumble serves its generic page, which is why a crawl "succeeds"
# and finds nothing). /c/KevinTrudeau answers 200 but lists no videos. So no new
# episode has entered the system since the change, and the catalogue is frozen at
# 632. FIND THE REAL ADDRESS FIRST - open the channel on his Mac and read the URL
# from the address bar - then this file and factory/rumble_stock.py both work again.

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
    try:
        from curl_cffi import requests as cr
        fetch = lambda: cr.get(url, impersonate="chrome", timeout=30)
    except ImportError:
        import urllib.request
        ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
        fetch = lambda: type("R", (), {"status_code": 200, "text": urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": ua}), timeout=30).read().decode("utf-8", "replace")})
    for attempt in range(5):
        try:
            r = fetch()
            if r.status_code == 200 and '"object_type":"video"' in r.text:
                return r.text
        except Exception:
            pass
        time.sleep(3 * (attempt + 1))
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
    json.dump(cat, open(OUT, "w"), indent=1, ensure_ascii=False)
    full = [e for e in cat.values() if not e["short"] and e["dur"] >= 1200]
    print(f"{len(cat)} videos, {len(full)} full episodes, {sum(1 for e in full if e['height'] >= 1080)} at 1080p+")


if __name__ == "__main__":
    main()
