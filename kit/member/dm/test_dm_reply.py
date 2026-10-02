#!/usr/bin/env python3
"""Comment -> DM, checked against a fake Meta API. Run: python3 dm/test_dm_reply.py

Proves: a whole-word keyword in any case gets ONE DM, 'brainstorm' does not,
comments older than Meta's 7-day window are skipped, the member's own comments
are skipped, a second run sends nothing twice, and the disclosure always rides."""
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
        return R({"data": [{"id": "M1", "timestamp": iso(timedelta(days=1))}]})
    if url.endswith("/M1/comments"):
        return R({"data": [
            {"id": "c1", "text": "Brain!", "timestamp": iso(timedelta(hours=2)), "username": "ann"},
            {"id": "c2", "text": "brainstorm idea", "timestamp": iso(timedelta(hours=2)), "username": "bob"},
            {"id": "c3", "text": "BRAIN", "timestamp": iso(timedelta(days=9)), "username": "old"},
            {"id": "c4", "text": "money please", "timestamp": iso(timedelta(hours=1)), "username": "cy"},
            {"id": "c5", "text": "Comment BRAIN for the link", "timestamp": iso(timedelta(hours=1)), "username": "me_myself"}]})
    if url.endswith("/PG/video_reels"):
        return R({"data": [{"id": "V1"}]})
    if url.endswith("/V1/comments"):
        return R({"data": [
            {"id": "f1", "message": "MONEY", "created_time": iso(timedelta(hours=3)), "from": {"id": "u9"}},
            {"id": "f2", "message": "money", "created_time": iso(timedelta(hours=3)), "from": {"id": "PG"}}]})
    raise AssertionError(url)


def post(url, params=None, json=None, timeout=None):
    sent.append((json["recipient"]["comment_id"], json["message"]["text"]))
    return R({"message_id": "mid"})


m.requests.get, m.requests.post = get, post
m.STATE = os.path.join(tempfile.mkdtemp(), "dms.json")
os.environ.update(DM_AUTO="on", OFFER_URL="https://example.com/me", KT_CTA_KEYWORDS="BRAIN,MONEY",
                  IG_USER_ID="IG", IG_ACCESS_TOKEN="it", FB_PAGE_ID="PG", FB_ACCESS_TOKEN="ft")
m.run()
first = sorted(c for c, _ in sent)
m.run()
assert first == ["c1", "c4", "f1"], first
assert len(sent) == 3, "a second run must send nothing"
assert all("#ad" in t and "https://example.com/me" in t for _, t in sent)
assert set(json.load(open(m.STATE))["sent"]) == {"c1", "c4", "f1"}
print("comment -> DM: all checks pass")
