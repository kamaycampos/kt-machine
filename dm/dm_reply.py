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
    DM_BRAND=AR_ python3 dm/dm_reply.py   # Awakened Rise: AR_* keys, state/dms_ar.json
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# AWAKENED RISE TOO (2 Nov 2026). Her captions ask for RISE/LUCKY and Meta's own rule
# answered none of them: 7 keyword comments, 0 replies. DM_BRAND=AR_ runs this same bot
# on her AR_* keys with her own link and its own state file - never Kevin's text or link.
BRAND = os.environ.get("DM_BRAND", "")
STATE = os.path.join(ROOT, "state", "dms_ar.json" if BRAND == "AR_" else "dms.json")
# ANSWERED BY HAND BEFORE THE BOT COULD (3 Nov 2026, Yaren: "i already manually sent
# messages to the people who commented"). A DM sent by hand leaves no public reply, so the
# bot cannot see it: everything older than this is hers, never DMed a second time.
SINCE = os.environ.get("DM_SINCE") or {"AR_": "2026-11-03T03:30:00"}.get(BRAND, "")
G = "https://graph.facebook.com/v21.0"
T = 30
WINDOW = timedelta(days=7)           # Meta's private-reply window
# comments arrive on the newest posts. The 2-3 minute pass (pulse.yml) reads only the
# newest few to stay far under Meta's rate limits; the 20-minute sweep reads 25.
RECENT_POSTS = int(os.environ.get("DM_RECENT_POSTS") or 25)
MAX_PER_RUN = 60                     # stay far under Meta's messaging limits
# THE FAST PASS (12 Nov 2026, Kamay: "it needs to be instantly"). A reply waited up to 2.5 min on
# the newest 6 posts and up to 20 min on any older clip. DM_FAST=1 is a pass cheap enough to run
# every 15 seconds on the newest 25 posts: ONE call lists them with their comment counts, and a
# post's comments are read only when its count moved since the last pass (kept in /tmp, the
# heartbeat's own disk). Instagram only; Facebook and anything a fast pass failed on are still
# caught by the ordinary pass every 2.5 minutes.
FAST = os.environ.get("DM_FAST") == "1"
COUNTS = f"/tmp/dm_counts_{BRAND or 'KT'}.json"


def _counts():
    try:
        return json.load(open(COUNTS))
    except (OSError, ValueError):
        return {}
# 14 Oct 2026, Kamay: the "#ad - I earn a commission" line is gone from the DM.
# {disclosure} stays accepted (empty) so an older DM_TEXT never breaks the send.
DEFAULT_TEXT = "Here it is: {link}"


def env(name):
    return os.environ.get(BRAND + name, "")


def keywords():
    if BRAND:                            # fail closed: never answer Kevin's words on her account
        raw = env("CTA_KEYWORDS")
    else:
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
    media = _get(f"{G}/{ig}/media", {"fields": "id,timestamp,comments_count", "limit": RECENT_POSTS,
                                       "access_token": tok}).get("data", [])
    diag = os.environ.get("DM_DIAG") == "1"
    out = []
    seen_counts = _counts()
    for m in media:
        if _ts(m["timestamp"]) < datetime.now(timezone.utc) - WINDOW - timedelta(days=30):
            continue
        if m.get("comments_count") == 0 and not diag:
            continue                     # nothing to read: save the call
        if FAST and seen_counts.get(m["id"]) == m.get("comments_count"):
            continue                     # nobody commented since the last look
        cs = _get(f"{G}/{m['id']}/comments", {"fields": "id,text,timestamp,username,replies{username}",
                                               "limit": 50, "access_token": tok}).get("data", [])
        if diag:
            print(f"  post {m['timestamp'][:16]}: says {m.get('comments_count')} comments, API gave {len(cs)}"
                  f" {[(c.get('text') or '')[:12] for c in cs]}")
        # A COMMENT WITH NO TEXT IS NEVER AN ASK (4 Nov 2026). A GIF or sticker comes back with no
        # text - and so does a real "RISE" whose words Instagram withheld (a flagged account).
        # Nothing in the API tells them apart, so for one evening blanks on a "Comment RISE" post
        # were DMed; Yaren: a GIF-only comment "got the link, that's not right". Instagram also
        # hid that DM from the flagged account, so answering blanks gained nothing. Only words count.
        out += [(c["id"], c.get("text") or "", c["timestamp"], m["id"], c.get("username", ""),
                 {r.get("username", "") for r in (c.get("replies") or {}).get("data", [])})
                for c in cs]
        seen_counts[m["id"]] = m.get("comments_count")
    try:
        json.dump(seen_counts, open(COUNTS, "w"))
    except OSError:
        pass
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
                 (c.get("from") or {}).get("id", ""), set()) for c in cs]
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
    link = env("OFFER_URL").strip()
    if not link.startswith("https://"):
        print("comment -> DM needs your link: set the OFFER_URL secret")
        return 0
    # DM_TEXT is Kevin's (his links are written into it); a brand uses its own or the plain line
    text = (env("DM_TEXT") or (BRAND and "Hey! Thanks for commenting. Here it is: {link}")
            or DEFAULT_TEXT).format(link=link, disclosure="").strip()
    kws, d, now = keywords(), load(), datetime.now(timezone.utc)
    if not kws:
        print(f"comment -> DM ({BRAND or 'KT'}): no keywords set ({BRAND}CTA_KEYWORDS)")
        return 0
    page, ftok = env("FB_PAGE_ID"), env("FB_ACCESS_TOKEN")
    ig, itok = env("IG_USER_ID"), env("IG_ACCESS_TOKEN")
    me = {page, ig}
    if ig and itok:                      # their own replies never DM themselves
        name = _counts().get("_me") if FAST else None
        if not name:
            try:
                name = _get(f"{G}/{ig}", {"fields": "username", "access_token": itok}).get("username", "")
                c_ = _counts()
                c_["_me"] = name
                json.dump(c_, open(COUNTS, "w"))
            except Exception:
                name = ""
        me.add(name or "")
    sources = []
    if ig and itok and page:
        # Read with the Page token when there is one: it carries instagram_manage_comments.
        # 14 Oct 2026: the Instagram token saw 5 comments in a week and missed a real
        # "Money" - it was never granted comment access.
        sources.append(("instagram", lambda: instagram_comments(ig, ftok or itok), ftok or itok))
    if page and ftok and not FAST:
        sources.append(("facebook", lambda: facebook_comments(page, ftok), ftok))
    if not sources:
        print("comment -> DM needs Instagram/Facebook connected (type `post` in Claude)")
        return 0
    sent = 0
    tally = {"keyword comments": 0, "already answered": 0, "outside 7 days": 0, "failed": 0,
             "waiting for permission": 0}
    for platform, fetch, tok in sources:
        blocked = False
        try:
            comments = fetch()
        except Exception as e:
            d["errors"].append({"at": now.isoformat(), "platform": platform, "error": str(e)})
            print(f"{platform}: could not read comments - {e}")
            continue
        for cid, body, when, post, author, repliers in comments:
            if blocked:
                if (matched(body, kws) and cid not in d["sent"] and cid not in d["seen"]
                        and author not in me and not repliers & me):
                    tally["waiting for permission"] += 1
                continue
            if cid in d["sent"] or cid in d["seen"] or author in me:
                continue
            # ALREADY ANSWERED BY THE ACCOUNT ITSELF (14 Oct 2026). Meta's own comment
            # rule replies in public ("Just sent it to you") as it sends its DM. If that
            # rule is working, this comment is taken care of - two DMs to one person is
            # the one mistake this must never make.
            if repliers & me:
                d["seen"][cid] = now.isoformat()
                tally["already answered"] += matched(body, kws) is not None
                continue
            d["seen"][cid] = now.isoformat()
            if SINCE and when[:19] < SINCE:
                continue
            kw = matched(body, kws)
            if not kw:
                continue
            tally["keyword comments"] += 1
            if now - _ts(when) > WINDOW:
                tally["outside 7 days"] += 1
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
                # THE PUBLIC REPLY, like Meta's own rule did (14 Oct 2026, Kamay: "before it
                # replied to the comment"). It tells the viewer to check their messages -
                # a DM from a page they don't follow lands in Requests - and other viewers
                # see that commenting works. Never fatal: the DM is what matters.
                if platform == "instagram" and os.environ.get("DM_PUBLIC_REPLY", "on") != "off":
                    try:
                        r = requests.post(f"{G}/{cid}/replies", timeout=T, params={
                            "message": os.environ.get("DM_PUBLIC_TEXT") or "Just sent it to you - check your messages \U0001F4E9",
                            "access_token": tok})
                        rec["public_reply"] = "ok" if r.ok and "id" in (r.json() or {}) else (r.json() or {}).get("error", {}).get("message", "")[:120]
                    except Exception as e:
                        rec["public_reply"] = f"error: {type(e).__name__}"
            except Exception as e:
                d["errors"] = [x for x in d["errors"] if x.get("error") != str(e) or x.get("platform") != platform]
                d["errors"].append({"at": now.isoformat(), "platform": platform,
                                    "comment": cid, "error": str(e)})
                # THE KEY CANNOT SEND AT ALL (2 Nov 2026: Awakened Rise's key had no
                # instagram_manage_messages). That is not this viewer's failure: spending
                # their 3 tries would drop them before the key is fixed. Leave every keyword
                # comment unanswered-and-unseen, so the first pass with the right key sends.
                if "permission" in str(e).lower() or "(#230)" in str(e) or "(#10)" in str(e):
                    d["seen"].pop(cid, None)
                    tally["waiting for permission"] += 1
                    blocked = True
                    print(f"{platform}: the key cannot send DMs - {e}")
                    continue
                tally["failed"] += 1
                # A FAILED SEND IS NOT A HANDLED COMMENT (14 Oct 2026). It stayed "seen",
                # so when the missing permission was granted, the viewer who asked
                # (a real "Money" comment) was never answered. Retry on later runs,
                # at most 3 times, inside Meta's 7-day window.
                tries = d.setdefault("tries", {})
                tries[cid] = tries.get(cid, 0) + 1
                if tries[cid] < 3:
                    d["seen"].pop(cid, None)
    if not dry:
        save(d)
    print(f"comment -> DM{' (' + BRAND.strip('_') + ')' if BRAND else ''}: {sent} sent this run, {len(d['sent'])} total | "
          + ", ".join(f"{k} {v}" for k, v in tally.items()))
    return 0


if __name__ == "__main__":
    sys.exit(run(dry="--dry" in sys.argv))
