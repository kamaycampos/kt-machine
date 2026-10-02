#!/usr/bin/env python3
"""COMMENT -> DM. A viewer comments the keyword; they get the link in their DMs.

Kamay, 2 Oct 2026: make it COMPLETE, end to end - "no manual step left to you".
The keyword is the only thing that carries the link: Instagram and TikTok
captions cannot hold one, and a comment-keyword ask measured 3.47 comments per
1,000 views against 1.60 for a question (factory/MASTERY.md, finding 19).

Every posting run (20 minutes) this:
  1. reads the newest comments on the member's recent Instagram and Facebook posts
  2. finds the ones that say one of their keywords (KT_CTA_KEYWORDS)
  3. sends each of those people ONE private reply with the link (OFFER_URL),
     using Meta's own Private Replies API - the same mechanism Meta's built-in
     automation and ManyChat use
  4. writes it all to state/dms.json, which the control panel turns into
     comments and DMs per keyword per 1,000 views

Never twice to the same comment, never to the member's own comments, only
inside Meta's 7-day private-reply window. Switched on by the repository
variable DM_AUTO = on, which the member's Claude sets during `post`.

    python3 dm/dm_reply.py            # one pass
    python3 dm/dm_reply.py --dry      # show what it would send, send nothing
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state", "dms.json")
G = "https://graph.facebook.com/v21.0"
T = 30
WINDOW = timedelta(days=7)           # Meta's private-reply window
RECENT_POSTS = 25                    # comments arrive on the newest posts
MAX_PER_RUN = 60                     # stay far under Meta's messaging limits
DISCLOSURE = "#ad - I earn a commission if you buy through my link."
DEFAULT_TEXT = "Here it is: {link}\n\n{disclosure}"


def keywords():
    raw = os.environ.get("KT_CTA_KEYWORDS", "") or "WISH,KT,FREE,YES"
    return [k.strip().upper() for k in raw.split(",") if k.strip()]


def matched(text, kws):
    """The keyword the comment says, as a whole word, any case. 'brain!' counts,
    'brainstorm' does not."""
    up = (text or "").upper()
    for k in kws:
        if re.search(r"(?<![A-Z0-9])" + re.escape(k) + r"(?![A-Z0-9])", up):
            return k
    return None


def load():
    try:
        d = json.load(open(STATE))
    except (OSError, ValueError):
        d = {}
    d.setdefault("sent", {})
    d.setdefault("seen", {})
    d.setdefault("errors", [])
    return d


def save(d):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    d["errors"] = d["errors"][-30:]
    # seen ids older than the window can never be answered again - drop them
    cutoff = (datetime.now(timezone.utc) - WINDOW - timedelta(days=1)).isoformat()
    d["seen"] = {k: v for k, v in d["seen"].items() if v >= cutoff}
    json.dump(d, open(STATE, "w"), indent=1)


def _get(url, params):
    r = requests.get(url, params=params, timeout=T)
    j = r.json() if r.content else {}
    if "error" in j:
        raise RuntimeError(j["error"].get("message", "graph error")[:200])
    return j


def _ts(t):
    return datetime.strptime(t[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def instagram_comments(ig, tok):
    """(comment_id, text, when, media_id, author) on the newest posts."""
    media = _get(f"{G}/{ig}/media", {"fields": "id,timestamp", "limit": RECENT_POSTS,
                                       "access_token": tok}).get("data", [])
    out = []
    for m in media:
        if _ts(m["timestamp"]) < datetime.now(timezone.utc) - WINDOW - timedelta(days=30):
            continue
        cs = _get(f"{G}/{m['id']}/comments", {"fields": "id,text,timestamp,username",
                                               "limit": 50, "access_token": tok}).get("data", [])
        out += [(c["id"], c.get("text", ""), c["timestamp"], m["id"], c.get("username", ""))
                for c in cs]
    return out


def facebook_comments(page, tok):
    reels = _get(f"{G}/{page}/video_reels", {"fields": "id", "limit": RECENT_POSTS,
                                             "access_token": tok}).get("data", [])
    out = []
    for v in reels:
        cs = _get(f"{G}/{v['id']}/comments", {"fields": "id,message,created_time,from",
                                              "limit": 50, "filter": "stream",
                                              "access_token": tok}).get("data", [])
        out += [(c["id"], c.get("message", ""), c["created_time"], v["id"],
                 (c.get("from") or {}).get("id", "")) for c in cs]
    return out


def private_reply(page, tok, comment_id, text):
    """Meta's Private Replies: one message to the person who left the comment.
    The same call, with the Page token, answers an Instagram comment (the account
    is linked to the Page) and a Facebook Page comment. Needs the Page token to
    carry pages_messaging and instagram_manage_messages - SETUP_POSTING.md."""
    r = requests.post(f"{G}/{page}/messages", timeout=T, params={"access_token": tok},
                      json={"recipient": {"comment_id": comment_id},
                            "message": {"text": text}})
    j = r.json() if r.content else {}
    if "error" in j:
        raise RuntimeError(j["error"].get("message", "send failed")[:200])
    return j.get("message_id", "sent")


def run(dry=False):
    if os.environ.get("DM_AUTO", "").lower() != "on" and not dry:
        print("comment -> DM is off (repository variable DM_AUTO is not 'on')")
        return 0
    link = os.environ.get("OFFER_URL", "").strip()
    if not link.startswith("https://"):
        print("comment -> DM needs your link: set the OFFER_URL secret")
        return 0
    text = (os.environ.get("DM_TEXT") or DEFAULT_TEXT).format(link=link, disclosure=DISCLOSURE)
    if DISCLOSURE not in text:
        text += "\n\n" + DISCLOSURE              # the disclosure is never optional
    kws, d, now = keywords(), load(), datetime.now(timezone.utc)
    page, ftok = os.environ.get("FB_PAGE_ID", ""), os.environ.get("FB_ACCESS_TOKEN", "")
    ig, itok = os.environ.get("IG_USER_ID", ""), os.environ.get("IG_ACCESS_TOKEN", "")
    me = {page, ig}
    if ig and itok:                      # their own replies never DM themselves
        try:
            me.add(_get(f"{G}/{ig}", {"fields": "username", "access_token": itok}).get("username", ""))
        except Exception:
            pass
    sources = []
    if ig and itok and page:
        sources.append(("instagram", lambda: instagram_comments(ig, itok), ftok or itok))
    if page and ftok:
        sources.append(("facebook", lambda: facebook_comments(page, ftok), ftok))
    if not sources:
        print("comment -> DM needs Instagram/Facebook connected (type `post` in Claude)")
        return 0
    sent = 0
    for platform, fetch, tok in sources:
        try:
            comments = fetch()
        except Exception as e:
            d["errors"].append({"at": now.isoformat(), "platform": platform, "error": str(e)})
            print(f"{platform}: could not read comments - {e}")
            continue
        for cid, body, when, post, author in comments:
            if cid in d["sent"] or cid in d["seen"] or author in me:
                continue
            d["seen"][cid] = now.isoformat()
            kw = matched(body, kws)
            if not kw:
                continue
            if now - _ts(when) > WINDOW:
                continue
            if sent >= MAX_PER_RUN:
                d["seen"].pop(cid, None)          # next run picks it up
                continue
            rec = {"platform": platform, "post": post, "keyword": kw,
                   "comment_at": when, "sent_at": now.isoformat()}
            if dry:
                print(f"would DM {platform} comment {cid} ({kw})")
                continue
            try:
                rec["message"] = private_reply(page, tok, cid, text)
                d["sent"][cid] = rec
                sent += 1
            except Exception as e:
                d["errors"].append({"at": now.isoformat(), "platform": platform,
                                    "comment": cid, "error": str(e)})
    if not dry:
        save(d)
    print(f"comment -> DM: {sent} sent this run, {len(d['sent'])} total")
    return 0


if __name__ == "__main__":
    sys.exit(run(dry="--dry" in sys.argv))
