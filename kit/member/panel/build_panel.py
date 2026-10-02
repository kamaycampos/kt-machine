#!/usr/bin/env python3
"""THE CONTROL PANEL - the member's own website for their whole factory.

Kamay, 2 Oct 2026: "build the most clear useful simple complete own website ...
so they can visually see and have control and see their system of clips,
descriptions, sources and where it's coming, edit that source, change things,
... data, statistics, reach, scores, pending, new updates and possibilities."

Written on every posting run (every 20 minutes) into docs/index.html and served
by GitHub Pages, so it is always current and costs nothing. The captions board
that build_pages.py writes moves to docs/captions.html.

Every "change this" on the panel is real: it opens the exact file in GitHub's
own editor (the member is already signed in), or copies the sentence to say to
their Claude. Nothing on the page pretends to save what it cannot.

    python3 panel/build_panel.py
"""
import html
import json
import os
import re
import statistics
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
REPO = os.environ.get("GITHUB_REPOSITORY") or "YOUR-GITHUB-NAME/YOUR-REPO"


def load(rel, default):
    try:
        return json.load(open(os.path.join(ROOT, rel)))
    except (OSError, ValueError):
        return default


def read(rel):
    try:
        return open(os.path.join(ROOT, rel), encoding="utf-8").read()
    except OSError:
        return ""


def latest_metrics(rows):
    """The newest sample per clip - metrics.json is a log, not a table."""
    out = {}
    for r in rows if isinstance(rows, list) else []:
        f = r.get("file")
        if f and (f not in out or r.get("at", "") >= out[f].get("at", "")):
            out[f] = r
    return out


def episode_index():
    """rumble id -> (title, url), from the catalog and the month's list."""
    idx = {}
    for url, v in (load("factory/rumble_catalog.json", {}) or {}).items():
        m = re.search(r"/(v[0-9a-z]+)-", url)
        if m:
            idx[m.group(1)] = {"title": v.get("title", ""), "url": url}
    for e in load("factory/source_plan.json", {}).get("episodes", []):
        idx.setdefault(e.get("id"), {"title": e.get("title", ""), "url": e.get("url", "")})
    return idx


def series_index():
    """(brand, slug) -> source + in/out, from what the factory built."""
    idx = {}
    for v in (load("factory/kt_series.json", {}) or {}).values():
        for c in v.get("clips", []):
            idx[(v.get("brand"), c.get("slug"))] = {
                "source": v.get("source", ""), "in": c.get("in"), "out": c.get("out")}
    return idx


def clip_rows():
    man = load("state/manifest.json", {}).get("clips", [])
    met = latest_metrics(load("state/metrics.json", []))
    tt = (load("state/tiktok.json", {}) or {}).get("videos", {}) or {}
    thumbs = load("docs/thumbs.json", {}) or {}
    eps, ser = episode_index(), series_index()
    rows = []
    for c in man:
        f = c.get("file", "")
        brand, _, name = f.partition("/")
        m = re.match(r"^\d+_(.+?)_(\d+)s\.mp4$", name)
        slug, secs = (m.group(1), int(m.group(2))) if m else (name, None)
        s = ser.get((brand, slug), {})
        sid = re.sub(r"\.mp4$", "", s.get("source", ""))
        ep = eps.get(sid, {})
        mm = met.get(f, {})
        ig = mm.get("instagram") or {}
        if not m:   # older names carry no length suffix
            slug = re.sub(r"^\d+_|_\d+s$|\.mp4$", "", name)
            slug = re.sub(r"_\d+s$", "", slug)
        slug = re.sub(r"^(\d+_)+", "", slug)      # some names carry the index twice
        hook = c.get("hook") or slug.replace("-", " ").capitalize()
        live = c.get("posted_at") or ("yes" if any(v == "posted" for v in (c.get("status") or {}).values()) else None)
        if isinstance(hook, list):
            hook = " ".join(hook)
        rows.append({
            "file": f, "brand": brand, "hook": hook, "secs": secs,
            "thumb": thumbs.get(f, ""), "caption": c.get("caption", ""),
            "status": c.get("status") or {}, "links": c.get("links") or {},
            "scheduled": c.get("scheduled_at"), "posted": live or None,
            "done": bool(c.get("done")), "retired": bool(c.get("retired")),
            "keyword": c.get("cta_keyword", ""),
            "views": {"instagram": ig.get("views"),
                      "youtube": (mm.get("youtube") or {}).get("views"),
                      "tiktok": (tt.get(f) or {}).get("view_count")},
            "skip": ig.get("reels_skip_rate"), "shares": ig.get("shares"),
            "saves": ig.get("saved"),
            "watch": round(ig["ig_reels_avg_watch_time"] / 1000, 1)
                     if ig.get("ig_reels_avg_watch_time") else None,
            "source": {"id": sid, "title": ep.get("title") or sid, "url": ep.get("url", ""),
                       "in": s.get("in"), "out": s.get("out")},
            "media": f"https://github.com/{REPO}/releases/download/media/{f.replace('/', '--')}",
        })
    return rows


def summary(rows):
    posted = [r for r in rows if r["posted"]]
    pending = [r for r in rows if not r["posted"] and not r["retired"]]
    views = sum(v or 0 for r in rows for v in r["views"].values())
    skips = [r["skip"] for r in rows if r["skip"] is not None]
    prof = (load("state/tiktok.json", {}) or {}).get("profile") or {}
    return {"made": len(rows), "posted": len(posted), "pending": len(pending),
            "views": views, "skip": round(statistics.median(skips), 1) if skips else None,
            "followers": prof.get("follower_count")}


def sources():
    eps = load("factory/source_plan.json", {}).get("episodes", [])
    done = set(load("factory/plans/_done.json", []))
    out = []
    for e in eps:
        eid = e.get("id", "")
        out.append({"id": eid, "title": e.get("title", eid), "url": e.get("url", ""),
                    "planned": f"ep_{eid}" in done or os.path.exists(
                        os.path.join(ROOT, "factory", "plans", f"ep_{eid}.json"))})
    return out


def dm_stats(rows):
    """Comment -> DM, per keyword: DMs sent, and DMs per 1,000 Instagram views on
    the clips that asked for that keyword (MASTERY finding 19 measured 3.47)."""
    d = load("state/dms.json", {}) or {}
    sent = list((d.get("sent") or {}).values())
    by = {}
    for r in sent:
        k = by.setdefault(r.get("keyword", "?"), {"keyword": r.get("keyword", "?"), "dms": 0,
                                                    "instagram": 0, "facebook": 0, "views": 0})
        k["dms"] += 1
        k[r.get("platform", "instagram")] = k.get(r.get("platform", "instagram"), 0) + 1
    for c in rows:
        kw = (c.get("keyword") or "").upper()
        if kw in by:
            by[kw]["views"] += c["views"].get("instagram") or 0
    for k in by.values():
        k["per_1k"] = round(k["dms"] * 1000 / k["views"], 2) if k["views"] else None
    week = (datetime.now(timezone.utc).timestamp() - 7 * 86400)
    recent = sum(1 for r in sent if _when(r.get("sent_at")) >= week)
    return {"total": len(sent), "week": recent, "keywords": sorted(by.values(), key=lambda x: -x["dms"]),
            "errors": (d.get("errors") or [])[-5:],
            "on": bool(sent) or bool(d.get("seen"))}


def _when(t):
    try:
        return datetime.fromisoformat(str(t)).timestamp()
    except ValueError:
        return 0


def build():
    os.makedirs(DOCS, exist_ok=True)
    board = os.path.join(DOCS, "index.html")
    if os.path.exists(board) and "factory-panel" not in read("docs/index.html"):
        os.replace(board, os.path.join(DOCS, "captions.html"))
    rows = clip_rows()
    data = {
        "repo": REPO,
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "kit": load("KIT.json", {}),
        "summary": summary(rows),
        "dms": dm_stats(rows),
        "clips": sorted(rows, key=lambda r: r["scheduled"] or r["posted"] or "", reverse=True),
        "sources": sources(),
        "style": {k: v for k, v in load("my_brand/style.json", {}).items() if not k.startswith("_")},
        "brand": read("my_brand/BRAND.md"),
        "report": read("factory/reports/latest.md")[-6000:],
    }
    page = TEMPLATE.replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
    open(board, "w", encoding="utf-8").write(page)
    print(f"panel built: {len(rows)} clips -> docs/index.html")


TEMPLATE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "panel.html"),
                encoding="utf-8").read()

if __name__ == "__main__":
    build()
