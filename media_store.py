#!/usr/bin/env python3
"""Which GitHub release holds a clip's video, and where the next one goes.

WHY THIS EXISTS. 7 Nov 2026: KT posted nothing for 34 hours with the queue at 0.
The clips were being built and PASSING - FIVE-FRIENDS-YOUR-INCOME, AR clips - but
every upload since 6 Nov 11:38 UTC failed with "file_count limited to 1000 assets
per release". Every clip, every __story / __yt59 cut and every trial-hook variant
had gone into the one release `media` since 13 Sept, and since 3 Nov (7 trial
hooks per clip) it filled at 30-75 files a day. add_clips printed UPLOAD FAILED,
the run still said success, and the manifest stayed frozen at 571 clips.

THE FIX: releases roll over - `media`, then `media2`, `media3`... A new clip goes
into the newest one with room for it AND its sidecars (a story cut must sit in the
same release as its clip: poster.py finds it by editing the clip's URL). The clip
records `media_tag` in the manifest (variant arms in variants.json), and every
reader resolves a URL through tag_for(). Old clips have no field = `media`, so
nothing already posted moves and nothing is deleted.
"""
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("MEDIA_TAG", "media")
LIMIT = 1000          # GitHub's hard cap on assets per release
SPARE = 10            # never fill a release to the last slot


def url(repo, tag, rel):
    return f"https://github.com/{repo}/releases/download/{tag}/" + rel.replace("/", "--")


_cache = {"key": None, "map": {}}


def _tags():
    """rel -> media_tag, from the manifest and the trial variants (re-read when they change)."""
    paths = [os.path.join(HERE, "state", "manifest.json"),
             os.path.join(HERE, "state", "variants.json")]
    key = tuple(os.path.getmtime(p) if os.path.exists(p) else 0 for p in paths)
    if key == _cache["key"]:
        return _cache["map"]
    m = {}
    try:
        for c in json.load(open(paths[0])).get("clips", []):
            if c.get("media_tag"):
                m[c["file"]] = c["media_tag"]
    except (OSError, ValueError):
        pass
    try:
        for e in json.load(open(paths[1])).values():
            for a in e.get("arms", []):
                if a.get("media_tag"):
                    m[a["rel"]] = a["media_tag"]
    except (OSError, ValueError, AttributeError):
        pass
    _cache.update(key=key, map=m)
    return m


def tag_for(rel):
    """The release holding `rel`. A sidecar (<clip>__story.mp4) lives with its clip."""
    m = _tags()
    if rel in m:
        return m[rel]
    base = re.sub(r"__[^/]*\.mp4$", ".mp4", rel)
    return m.get(base, BASE)


def url_for(repo, rel):
    return url(repo, tag_for(rel), rel)


class Store:
    """Picks the release a new upload goes into, creating the next one when full."""

    def __init__(self, gh, repo, log=print):
        self.gh, self.repo, self.log = gh, repo, log
        self.tag, self.count = None, 0

    def _run(self, *a):
        return subprocess.run([self.gh, *a, "-R", self.repo], capture_output=True, text=True)

    def _n(self, tag):
        return 1 if tag == BASE else int(tag[len(BASE):])

    def _newest(self):
        r = self._run("release", "list", "--limit", "200", "--json", "tagName",
                      "-q", ".[].tagName")
        tags = [t for t in r.stdout.split() if re.fullmatch(re.escape(BASE) + r"\d*", t)]
        return max(tags, key=self._n) if tags else BASE

    def _assets(self, tag):
        r = self._run("release", "view", tag, "--json", "assets", "-q", ".assets|length")
        return int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip().isdigit() else None

    def room(self, need):
        """A release tag with room for `need` more files."""
        if self.tag is None:
            self.tag = self._newest()
            self.count = self._assets(self.tag) or 0
        if self.count + need <= LIMIT - SPARE:
            return self.tag
        nxt = f"{BASE}{self._n(self.tag) + 1}"
        if self._assets(nxt) is None:
            r = self._run("release", "create", nxt, "--title", f"Clip media {self._n(nxt)}",
                          "--notes", "Clip videos, continued (GitHub caps a release at 1000 files). "
                          "See media_store.py.", "--target", "main", "--latest=false")
            if r.returncode:
                raise RuntimeError(f"could not create release {nxt}: {r.stderr[-200:]}")
            self.log(f"   NEW RELEASE {nxt}: {self.tag} is full ({self.count} files)")
        self.tag, self.count = nxt, self._assets(nxt) or 0
        return self.tag

    def used(self, n=1):
        self.count += n
