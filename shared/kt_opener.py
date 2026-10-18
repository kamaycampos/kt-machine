"""THE CINEMATIC OPENER - the editor's first build (factory/EDITOR.md, 17 Oct 2026).

Kamay: a clip with a great teaching and a bad picture does not get deleted; it opens on
"high quality cinematic living hooking images", and the teaching follows. Our own numbers
say why it matters: skip rate under 40% = 995 median views, over 50% = 284 (180 KT clips).

What it does, in the first OPEN_SECS seconds of a clip:
  - a 4K moving shot that IS the hook's subject (Pixabay, free, commercial use),
    cropped FULL-BLEED 9:16 (MASTERY #5: letterbox lost 20-100x), graded and pushed in;
  - Kevin's voice already running under it, so not a word of the teaching is lost;
  - a low hit under the voice at frame 1 (the sense we never used: FIRST_3_SECONDS #4);
  - a crossfade into Kevin; captions and the hook card ride on top the whole time.
Never film or TV footage. Every shot used is logged with its licence beside the clip.
"""
import json
import os
import subprocess
import urllib.parse
import urllib.request

HOME = os.environ.get("KT_HOME") or os.path.expanduser("~/Kamay")
FFMPEG = os.environ.get("WF_FFMPEG", os.path.join(HOME, "bin/ffmpeg"))
CACHE = os.path.join(HOME, "work/broll")
OPEN_SECS = 3.0
XFADE = 0.45
W, H = 1080, 1920
# Pixabay's firewall refuses Python's default User-Agent (403, error 1010).
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) kt-editor/1.0"


def _key():
    k = os.environ.get("PIXABAY_KEY")
    if k:
        return k
    p = os.path.join(HOME, ".stock.keys")
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("PIXABAY_KEY="):
                return line.split("=", 1)[1].strip()
    return None


_STOP = set("a an the of at in on with and or to for from by into over under very lone close up closeup "
             "slow motion slowmotion shot macro aerial cinematic night day golden hour vintage old new "
             "big small dark bright empty single".split())


def _content(query):
    """The words that name the picture: nouns and verbs, not the mood words."""
    ws = [w for w in query.lower().split() if len(w) > 2 and w not in _STOP]
    return ws or query.lower().split()


def search(query, n=12):
    """Pixabay videos for a query, best first: 4K, then editors' choice, then size."""
    k = _key()
    if not k:
        raise RuntimeError("no PIXABAY_KEY (run ~/Kamay/bin/stock_keys.py)")
    u = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode(
        {"key": k, "q": query, "per_page": n, "safesearch": "true", "video_type": "film"})
    hits = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}),
                                           timeout=30)).get("hits", [])
    # RELEVANCE FIRST, ON EVERY MEANINGFUL WORD (18 Oct 2026). Pixabay's own order put
    # tigers above the one basketball shot (17 Oct); then a first-word filter matched rain on
    # glass to "stack of hundred dollar bills" and found nothing for "lone office light at
    # night". A shot must carry at least half of the query's content words in its tags,
    # and more matching words rank first.
    words = _content(query)
    need = max(1, (len(words) + 1) // 2)
    for h in hits:
        tags = h.get("tags", "").lower()
        h["_match"] = sum(1 for w in words if w in tags)
    hits = [h for h in hits if h["_match"] >= need]

    def rank(h):
        big = h["videos"].get("large") or {}
        return (h.get("_match", 0), big.get("width", 0) >= 3840, big.get("width", 0), h.get("likes", 0))
    return sorted(hits, key=rank, reverse=True)


def fetch(hit):
    """Download one Pixabay video (largest rendition) into the cache, with its licence record."""
    os.makedirs(CACHE, exist_ok=True)
    v = hit["videos"].get("large") or hit["videos"].get("medium")
    path = os.path.join(CACHE, f"pixabay_{hit['id']}.mp4")
    if not os.path.exists(path):
        with urllib.request.urlopen(urllib.request.Request(v["url"], headers={"User-Agent": UA}),
                                    timeout=300) as r, open(path + ".part", "wb") as f:
            f.write(r.read())
        os.replace(path + ".part", path)
    json.dump({"source": "pixabay", "id": hit["id"], "page": hit.get("pageURL"),
               "user": hit.get("user"), "licence": "Pixabay Content License (free commercial use)",
               "size": f"{v.get('width')}x{v.get('height')}", "tags": hit.get("tags")},
              open(path[:-4] + ".json", "w"), indent=1)
    return path


def pick(query, secs=OPEN_SECS):
    """The shot for a plan's `opener` query: relevant, 4K first, long enough, and not
    one this machine used in its last 40 openers. Returns {"path", "start", "id"} or None
    (no key, no match, a network error) - the clip then renders as it always did."""
    used_p = os.path.join(CACHE, "_used.json")
    try:
        used = json.load(open(used_p))
    except Exception:
        used = []
    # The full query first, then its content words alone, then the last two (the noun
    # usually sits at the end: "lone office light at night" -> "office light").
    ws = _content(query)
    tries = [query, " ".join(ws), " ".join(ws[-2:]), ws[-1] if ws else query]
    hits = []
    for q in dict.fromkeys(t for t in tries if t):
        try:
            hits = [h for h in search(q, n=40)
                    if (h.get("duration") or 0) >= secs + 2
                    and max((h["videos"].get("large") or {}).get("width", 0),
                            (h["videos"].get("large") or {}).get("height", 0)) >= 1920]
        except Exception as e:
            print(f"      opener: search failed for '{q}' ({type(e).__name__})")
            return None
        if hits:
            if q != query:
                print(f"      opener: '{query}' found nothing usable; used '{q}'")
            break
    fresh = [h for h in hits if h["id"] not in used] or hits
    if not fresh:
        print(f"      opener: no usable shot for '{query}'")
        return None
    h = fresh[0]
    try:
        path = fetch(h)
    except Exception as e:
        print(f"      opener: download failed ({type(e).__name__})")
        return None
    used = ([h["id"]] + [u for u in used if u != h["id"]])[:40]
    os.makedirs(CACHE, exist_ok=True)
    json.dump(used, open(used_p, "w"))
    print(f"      opener: pixabay {h['id']} for '{query}' ({h.get('tags', '')[:50]})")
    return {"path": path, "start": 1.0, "id": h["id"], "query": query}


def sting(path=None, secs=1.6):
    """A low cinematic hit, synthesised (no licence question): a falling sub-boom plus a
    short air transient, mixed to sit UNDER a voice."""
    path = path or os.path.join(CACHE, "sting_hit.wav")
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    boom = "0.9*sin(2*PI*(38+70*exp(-9*t))*t)*exp(-2.6*t)"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                    "-f", "lavfi", "-i", f"aevalsrc='{boom}|{boom}':s=48000:d={secs}",
                    "-f", "lavfi", "-i", f"anoisesrc=d={secs}:c=pink:a=0.5:r=48000",
                    "-filter_complex",
                    "[1:a]highpass=f=900,lowpass=f=7000,afade=t=out:st=0:d=0.35,volume=0.35,"
                    "aformat=channel_layouts=stereo[air];"
                    "[0:a][air]amix=inputs=2:normalize=0,alimiter=limit=0.9[o]",
                    "-map", "[o]", "-c:a", "pcm_s16le", path], check=True)
    return path


def broll_chain(idx, secs=OPEN_SECS, push=0.08):
    """Filter for input #idx: cover 9:16 at full bleed, slow push-in, cinematic grade."""
    return (f"[{idx}:v]trim=duration={secs + 0.1:.2f},setpts=PTS-STARTPTS,fps=30,"
            f"scale={int(W * 1.6)}:{int(H * 1.6)}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={int(W * 1.6)}:{int(H * 1.6)},"
            f"zoompan=z='1+{push:.3f}*on/{int(secs * 30)}':d=1:s={W}x{H}:fps=30:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',"
            f"eq=contrast=1.07:saturation=1.12:brightness=-0.015,vignette=angle=PI/5,"
            f"noise=alls=4:allf=t,setsar=1,format=yuv420p,trim=duration={secs:.2f}")


def video_graph(geo, broll_idx, secs=OPEN_SECS, xd=XFADE):
    """[0:v] framed by `geo`, opened by the b-roll, crossfaded, out as [kv0]."""
    return (f"[0:v]{geo},format=yuv420p[kvf];"
            f"{broll_chain(broll_idx, secs)}[br];"
            f"[kvf]trim=start={secs - xd:.2f},setpts=PTS-STARTPTS[kvt];"
            f"[br][kvt]xfade=transition=fade:duration={xd:.2f}:offset={secs - xd:.2f}[kv0]")


def audio_graph(sting_idx, gain=0.3):
    """Voice + the hit under it, as [a0]."""
    return (f"[{sting_idx}:a]volume={gain:.2f},aformat=sample_rates=48000:channel_layouts=stereo[st];"
            f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo[vo];"
            f"[vo][st]amix=inputs=2:duration=first:normalize=0[a0]")
