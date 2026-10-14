#!/usr/bin/env python3
"""The Upload-Post route, checked against a fake API. Run: python3 engine/test_uploadpost.py

Proves: dormant without a key; a confirmed post returns ("posted", url); a background
job is polled until it confirms; a platform not connected in the dashboard is said
plainly; an unconfirmed job is NEVER reported as posted; every request carries the
same Idempotency-Key for the same clip and platform, so a retry cannot double-post."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.pop("UPLOADPOST_API_KEY", None)
import poster as p

clip = {"file": "KT_TEST/01_X_60s.mp4", "hook": "The 70x7 rule for your income"}
assert p.uploadpost_platforms("KT_TEST") == set(), "must be dormant without a key"

calls, mode = [], {"v": "sync"}


class R:
    def __init__(self, code, j):
        self.status_code, self._j, self.content = code, j, b"x"

    def json(self):
        return self._j


def post(url, headers=None, files=None, timeout=None):
    calls.append(headers["Idempotency-Key"])
    f = dict(files)
    assert f["platform[]"][1] in ("tiktok", "youtube") and f["video"][1].startswith("https://")
    if mode["v"] == "sync":
        return R(200, {"success": True, "results": {"tiktok": {"success": True, "url": "https://tiktok.com/@a/video/1"}}})
    if mode["v"] == "skipped":
        return R(200, {"success": True, "results": {"tiktok": {"skipped": True}}})
    return R(200, {"success": True, "request_id": "req-1", "total_platforms": 1})


polls = {"n": 0}


def get(url, headers=None, params=None, timeout=None):
    polls["n"] += 1
    if mode["v"] == "never":
        return R(200, {"completed": 0, "total": 1})
    if polls["n"] < 2:
        return R(200, {"completed": 0, "total": 1})
    return R(200, {"completed": 1, "total": 1,
                   "results": [{"platform": "youtube", "success": True, "url": "https://youtube.com/shorts/z"}]})


p.requests.post, p.requests.get, p.time.sleep = post, get, lambda s: None
os.environ.update(UPLOADPOST_API_KEY="k", UPLOADPOST_USER="me")
assert "tiktok" in p.uploadpost_platforms("KT_TEST")

assert p.via_uploadpost("tiktok", "x.mp4", "cap", "https://h/x.mp4", clip) == ("posted", "https://tiktok.com/@a/video/1")
mode["v"] = "async"
assert p.via_uploadpost("youtube", "x.mp4", "cap", "https://h/x.mp4", clip) == ("posted", "https://youtube.com/shorts/z")
mode["v"] = "skipped"
assert "not connected" in p.via_uploadpost("tiktok", "x.mp4", "cap", "https://h/x.mp4", clip)
mode["v"], polls["n"] = "never", 0
r = p.via_uploadpost("youtube", "x.mp4", "cap", "https://h/x.mp4", clip)
assert isinstance(r, str) and "not yet confirmed" in r, r
tik = [c for c in calls[:1]] + [calls[2]]
assert len(set(tik)) == 1, "the same clip + platform must reuse its Idempotency-Key"
print("upload-post route: all checks pass")
