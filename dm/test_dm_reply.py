#!/usr/bin/env python3
"""Comment -> DM, checked against a fake Meta API. Run: python3 dm/test_dm_reply.py

Proves: a whole-word keyword in any case gets ONE DM, 'brainstorm' does not,
comments older than Meta's 7-day window are skipped, the member's own comments
are skipped, a comment the account already answered (Meta's own rule) is skipped,
a second run sends nothing twice, and the link always rides with no #ad line."""
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dm_reply as m

now = datetime.now(timezone.utc)
iso = lambda d: (now - d).strftime("%Y-%m-%dT%H:%M:%S+0000")
sent = []


class R:
    content = b"x"

    def __init__(self, j):
        self._j = j

    def json(self):
        return self._j


def get(url, params=None, timeout=None):
    if url.endswith("/IG"):
        return R({"username": "me_myself"})
    if url.endswith("/IG/media"):
        return R({"data": [{"id": "M1", "timestamp": iso(timedelta(days=1))},
                           {"id": "M2", "timestamp": iso(timedelta(days=1)), "caption": "Comment MONEY and I’ll send it"},
                           {"id": "M3", "timestamp": iso(timedelta(days=1)), "caption": "No ask here. MONEY talk."}]})
    # 4 Nov 2026: Instagram withheld the text of a real "RISE" - blank on an asking post counts
    if url.endswith("/M2/comments"):
        return R({"data": [{"id": "c7", "timestamp": iso(timedelta(hours=1)), "username": "eve"}]})
    if url.endswith("/M3/comments"):
        return R({"data": [{"id": "c8", "text": "", "timestamp": iso(timedelta(hours=1)), "username": "fay"}]})
    if url.endswith("/M1/comments"):
        return R({"data": [
            {"id": "c1", "text": "Brain!", "timestamp": iso(timedelta(hours=2)), "username": "ann"},
            {"id": "c2", "text": "brainstorm idea", "timestamp": iso(timedelta(hours=2)), "username": "bob"},
            {"id": "c3", "text": "BRAIN", "timestamp": iso(timedelta(days=9)), "username": "old"},
            {"id": "c4", "text": "money please", "timestamp": iso(timedelta(hours=1)), "username": "cy"},
            {"id": "c5", "text": "Comment BRAIN for the link", "timestamp": iso(timedelta(hours=1)), "username": "me_myself"},
            {"id": "c6", "text": "MONEY", "timestamp": iso(timedelta(hours=1)), "username": "dee",
             "replies": {"data": [{"username": "me_myself"}]}}]})
    if url.endswith("/PG/video_reels"):
        return R({"data": [{"id": "V1"}]})
    if url.endswith("/V1/comments"):
        return R({"data": [
            {"id": "f1", "message": "MONEY", "created_time": iso(timedelta(hours=3)), "from": {"id": "u9"}},
            {"id": "f2", "message": "money", "created_time": iso(timedelta(hours=3)), "from": {"id": "PG"}}]})
    raise AssertionError(url)


def post(url, params=None, json=None, timeout=None):
    if url.endswith("/replies"):
        return R({"id": "r1"})
    sent.append((json["recipient"]["comment_id"], json["message"]["text"]))
    return R({"message_id": "mid"})


m.requests.get, m.requests.post = get, post
m.STATE = os.path.join(tempfile.mkdtemp(), "dms.json")
os.environ.update(DM_AUTO="on", OFFER_URL="https://example.com/me", KT_CTA_KEYWORDS="BRAIN,MONEY",
                  IG_USER_ID="IG", IG_ACCESS_TOKEN="it", FB_PAGE_ID="PG", FB_ACCESS_TOKEN="ft")
m.run()
first = sorted(c for c, _ in sent)
m.run()
assert first == ["c1", "c4", "c7", "f1"], first
assert len(sent) == 4, "a second run must send nothing"
assert all("#ad" not in t and "https://example.com/me" in t for _, t in sent)
assert set(json.load(open(m.STATE))["sent"]) == {"c1", "c4", "c7", "f1"}

# AWAKENED RISE (2 Nov 2026): her own keys, words and link; a key without DM permission
# leaves every keyword comment waiting, so the first pass with the right key answers them.
sent.clear()
real_post = post
refuse = [True]


def ar_post(url, params=None, json=None, timeout=None):
    if refuse[0] and not url.endswith("/replies"):
        return R({"error": {"message": "(#230) Requires instagram_manage_messages permission to manage the object"}})
    return real_post(url, params, json, timeout)


m.requests.post = ar_post
m.SINCE = ""
m.BRAND, m.STATE = "AR_", os.path.join(tempfile.mkdtemp(), "dms_ar.json")
os.environ.update(AR_OFFER_URL="https://example.com/her", AR_CTA_KEYWORDS="MONEY",
                  AR_IG_USER_ID="IG", AR_IG_ACCESS_TOKEN="it", AR_FB_PAGE_ID="PG", AR_FB_ACCESS_TOKEN="ft")
for _ in range(4):                       # more passes than the 3-try limit
    m.run()
assert sent == [], sent
d = json.load(open(m.STATE))
assert not d["sent"] and "c4" not in d["seen"] and "f1" not in d["seen"], d["seen"]
assert len(d["errors"]) <= 2, "one permission error per platform, not one per pass"
refuse[0] = False
m.run()
assert sorted(c for c, _ in sent) == ["c4", "c7", "f1"], sent      # MONEY only - BRAIN is Kevin's word
assert all(t == "Hey! Thanks for commenting. Here it is: https://example.com/her" for _, t in sent), sent
# comments from before the cutoff were answered by hand: never a second DM
sent.clear()
m.SINCE = (now + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S")
m.STATE = os.path.join(tempfile.mkdtemp(), "dms_ar.json")
m.run()
assert sent == [], sent
os.environ["AR_CTA_KEYWORDS"] = ""
assert m.keywords() == [], "her account must never fall back to Kevin's words"
print("comment -> DM: all checks pass")
