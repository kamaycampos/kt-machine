#!/usr/bin/env python3
"""THE COPY LAB (19 Nov 2026). Kamay, on Kevin's clip "AI replaced the $100,000 copywriter":
"that is what this project needs." Kevin's student built an AI that writes sales copy AND tested it
head to head; the machine already writes every hook and caption with AI, but nothing measured which
wording works. This does the measuring.

Every posted KT clip is sorted by the SHAPE of its words - the hook (a number, a question, "Kevin
says", a plain claim) and the caption's first line (keyword first, a question, "Kevin Trudeau says",
a story) - and each shape is scored on what the viewers did: views, and comments / shares / saves per
1,000 views on Instagram and TikTok. The weekly winners are written to factory/reports/copy_lab.md,
which PLANNING.md tells the planner to read before writing a hook or a caption.

    python factory/copy_lab.py          # writes factory/reports/copy_lab.md, prints the table
"""
import json
import os
import re
import statistics as st
from collections import defaultdict
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DAYS = int(os.environ.get("COPY_LAB_DAYS") or 45)
MIN_N = 4                                   # a shape seen fewer times than this is not scored


def load(p, default):
    try:
        return json.load(open(os.path.join(ROOT, p)))
    except (OSError, ValueError):
        return default


def hook_kind(h):
    h = " ".join(h) if isinstance(h, list) else str(h or "")
    if re.search(r"[$\d]", h):
        return "number in the hook"
    if "?" in h:
        return "question hook"
    if re.search(r"\bkevin\b|\bhe says\b", h, re.I):
        return "'Kevin says' hook"
    return "plain claim hook"


def opener_kind(cap):
    first = next((l.strip() for l in (cap or "").split("\n") if l.strip()), "")
    if re.match(r"(?i)(want|ready|need)\b.*comment|^comment\b", first):
        return "keyword first"
    if first.endswith("?"):
        return "question first"
    if re.search(r"(?i)kevin trudeau (says|said|explains|describes|brings)", first):
        return "'Kevin Trudeau says' first"
    return "story first"


def main():
    since = (datetime.utcnow() - timedelta(days=DAYS)).strftime("%Y-%m-%d")
    clips = {c["file"]: c for c in load("state/manifest.json", {}).get("clips", [])
             if c["file"].startswith("KT") and (c.get("posted_at") or "") >= since}
    ig = {}
    for r in load("state/metrics.json", []):
        if r["file"] in clips and (r.get("instagram") or {}).get("views") is not None:
            if r["file"] not in ig or r["at"] > ig[r["file"]]["at"]:
                ig[r["file"]] = r
    tt = {}
    vids = load("state/tiktok.json", {}).get("videos", {})
    for v in (vids.values() if isinstance(vids, dict) else vids):
        tt[str(v.get("id"))] = v
    rows = []
    for f, c in clips.items():
        i = (ig.get(f) or {}).get("instagram") or {}
        if not i.get("views"):
            continue
        t = tt.get(str(((c.get("links") or {}).get("tiktok_id")) or ""), {})
        cap = c.get("caption_at_post") or c.get("caption") or ""
        rows.append({"file": f, "hook": hook_kind(c.get("hook")), "open": opener_kind(cap),
                     "key": (c.get("cta_keyword") or "-").upper(), "len": "over 90 s"
                     if int((re.search(r"_(\d+)s", f) or [0, 0])[1]) > 90 else "90 s or less",
                     "views": i["views"], "c": i.get("comments", 0), "s": i.get("shares", 0),
                     "v": i.get("saved", 0), "tt_views": t.get("view_count")})
    out = [f"# Copy Lab - what the words did ({datetime.utcnow():%d %b %Y}, last {DAYS} days, "
           f"{len(rows)} KT clips with Instagram numbers)", "",
           "Per 1,000 Instagram views. A shape needs %d clips to be scored. Read this before writing a "
           "hook or a caption: lean toward the shapes on top, test the others less." % MIN_N, ""]
    for dim, title in (("hook", "Hook shape"), ("open", "Caption first line"), ("key", "Keyword"),
                       ("len", "Length")):
        g = defaultdict(list)
        for r in rows:
            g[r[dim]].append(r)
        scored = []
        for k, rs in g.items():
            if len(rs) < MIN_N:
                continue
            tv = sum(r["views"] for r in rs) or 1
            scored.append((sum(r["c"] + r["s"] + r["v"] for r in rs) * 1000 / tv, k, len(rs),
                           st.median(r["views"] for r in rs), sum(r["c"] for r in rs) * 1000 / tv,
                           sum(r["s"] for r in rs) * 1000 / tv, sum(r["v"] for r in rs) * 1000 / tv))
        scored.sort(reverse=True)
        out += [f"## {title}", "", "| shape | clips | median views | comments | shares | saves | all actions |",
                "|---|---|---|---|---|---|---|"]
        out += [f"| {k} | {n} | {med:.0f} | {c:.1f} | {s:.1f} | {v:.1f} | **{a:.1f}** |"
                for a, k, n, med, c, s, v in scored]
        out.append("")
    rep = os.path.join(HERE, "reports", "copy_lab.md")
    os.makedirs(os.path.dirname(rep), exist_ok=True)
    open(rep, "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
