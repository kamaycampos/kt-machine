#!/usr/bin/env python3
"""THE MUSIC THAT FITS THE STORY (15 Nov 2026).

Kamay on the first automatic movie clip: "the music is like meditating music, it is so off ...
with the black jack not at all. You must find the perfect matching music tracks for the clips,
as code pattern and strategic way, not just random."

It was nearly random: three calm ambient tracks, taken in turn. Now:
  1. every track in factory/music/ carries what it IS (tracks.json): the maker's own tags from
     its Pixabay page, an intensity of 1-3, and two things measured from the sound by this file
     (`scan`): its tempo and how steady it is;
  2. the story says what it NEEDS: the planner's mood words, plus what Kevin's own words are
     about - a lexicon turns "blackjack, dealer, casino" into casino / noir / suspense and
     "my dad, 1967, garage, never came home" into nostalgic / americana / emotional;
  3. the score is the overlap, weighted by how much of the story each theme fills, minus a
     penalty for the wrong intensity and for a track used in the last few clips. The last
     track used is never taken again. The whole score sheet is printed, so a wrong pick can be
     argued with.
A track marked "use": false (he called it too upbeat, or it is meditation music with nothing
to say) is never picked.  A story nothing fits well (best score under MIN_FIT) is reported.

    python factory/music_pick.py scan                  # measure every track, write tracks.json
    python factory/music_pick.py pick "story text" [mood,mood]   # show the score sheet
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MUSIC = os.path.join(HERE, "music")
TRACKS = os.path.join(MUSIC, "tracks.json")
K = os.path.expanduser("~/Kamay")
FF = os.path.join(K, "bin", "ffmpeg") if os.path.exists(os.path.join(K, "bin", "ffmpeg")) else "ffmpeg"
MIN_FIT = 2.0

# THE FAMILY (15 Nov 2026). Kamay on jazz under the blackjack story and guitar under the car
# story: "THE MUSIC IS A NO NO". Looked up what the reels we are measured against really use:
# their 233K "Private Jet" Episode carries the Instagram track "Kobe Mane - VIOLENTO" (420,000
# reels use it; phonk), their Alps Episode "Da Real Emkay - Casablanca (Addictive Mix)" (a deep
# house producer). Not library underscore, not jazz, not ambient: MODERN BEATS. Instagram's own
# tracks cannot be attached through the posting API, so the library now holds royalty-free
# tracks of that family (phonk / deep house / afro house) and the themes below point INTO it.
# A track outside the family is "use": false until Kamay has heard it.
# what Kevin's words are about -> what the music should be. (theme, intensity, words)
LEXICON = [
    (["phonk", "dark", "casino", "suspense"], 2,
     r"casino|blackjack|black jack|dealer|poker|roulette|\bcards?\b|\bbet\b|gambl|chips|vegas|reno|\bdeck\b"),
    (["phonk", "dark", "tension"], 2,
     r"police|arrest|fbi|prison|jail|judge|court|guards?|gorillas|cheat|caught|escape|chase|threat|mafia|godfather"),
    (["warm", "chill", "nostalgic", "afro"], 2,
     r"my dad|my father|my mother|my mom|grandfather|grandmother|when i was (a kid|young|\d+)|first car|19[3-8]\d|"
     r"garage|newspaper|high school|grew up|childhood|small town|convertible|camaro|firebird|cadillac"),
    (["warm", "chill", "emotional"], 2,
     r"never came home|died|passed away|funeral|vietnam|\bwar\b|cried|tears|lost (his|her|my)|goodbye|broke my heart"),
    (["dark", "phonk", "night"], 2,
     r"secret societ|brotherhood|skull and bones|hidden|classified|nobody knows|they don't want|initiat|the lodge|freemason"),
    (["luxury", "house", "inspiring"], 2,
     r"million|billion|company|business|\bdeal\b|sold|investor|private jet|yacht|rolls|mansion|wall street|built"),
    (["chill", "house", "wonder"], 2,
     r"universe|energy|frequenc|vibration|manifest|subconscious|consciousness|meditat|alien|quantum|the mind|brain wave"),
]


def tracks():
    return json.load(open(TRACKS))


def story_needs(text, mood=()):
    """(theme -> weight, intensity wanted) from Kevin's words and the planner's mood."""
    t = " " + re.sub(r"\s+", " ", (text or "").lower()) + " "
    need, hot = {}, []
    for themes, inten, rx in LEXICON:
        n = len(re.findall(rx, t))
        if n:
            w = min(3.0, 1.0 + 0.5 * (n - 1))
            for i, th in enumerate(themes):
                need[th] = need.get(th, 0) + w * (1.0 if i == 0 else 0.7)
            hot.append((w, inten))
    for m in mood or ():
        need[m.lower()] = need.get(m.lower(), 0) + 1.5
    inten = round(sum(w * i for w, i in hot) / sum(w for w, _ in hot)) if hot else 1
    return need, inten


def pick(text, mood=(), used=(), log=print):
    tr = {f: t for f, t in tracks().items() if t.get("use", True) and os.path.exists(os.path.join(MUSIC, f))}
    need, inten = story_needs(text, mood)
    used = list(used or [])
    rows = []
    for f, t in tr.items():
        tags = set(t.get("tags", []))
        fit = sum(w for th, w in need.items() if th in tags)
        off = 0.8 * abs(int(t.get("intensity", 1)) - inten)
        recent = 1.5 if f in used[-4:] else 0.0
        banned = bool(used) and f == used[-1] and len(tr) > 1
        rows.append((fit - off - recent - (99 if banned else 0), fit, f, sorted(tags & set(need))))
    rows.sort(reverse=True)
    log(f"    music: the story needs {', '.join(f'{k} {v:.1f}' for k, v in sorted(need.items(), key=lambda x: -x[1])) or 'nothing named'}"
        f" (intensity {inten})")
    for score, fit, f, hit in rows[:4]:
        log(f"      {score:5.1f}  {f}  [{', '.join(hit)}]")
    if not rows:
        return None
    if rows[0][1] < MIN_FIT:
        log(f"    music: NOTHING FITS WELL (best {rows[0][1]:.1f}) - the library needs a track for this kind of story")
    return rows[0][2]


def scan():
    """Tempo and steadiness of every track, from the sound itself."""
    import numpy as np
    tr = tracks()
    for f in sorted(os.listdir(MUSIC)):
        if not f.endswith(".mp3"):
            continue
        raw = subprocess.run([FF, "-loglevel", "error", "-t", "90", "-i", os.path.join(MUSIC, f), "-ac", "1", "-ar", "11025",
                              "-f", "s16le", "-"], capture_output=True).stdout
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        hop = 256
        n = len(x) // hop
        env = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-9)
        on = np.maximum(0, np.diff(np.log(env + 1e-4)))
        on = on - on.mean()
        ac = np.correlate(on, on, "full")[len(on) - 1:]
        fps = 11025 / hop
        lo, hi = int(fps * 60 / 170), int(fps * 60 / 55)
        lag = lo + int(np.argmax(ac[lo:hi]))
        e = tr.setdefault(f, {"tags": [], "intensity": 1, "use": False, "note": "NEW - needs tags from its page"})
        e["bpm"] = round(60 * fps / lag)
        e["level_db"] = round(float(20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)), 1)
        e["swing_db"] = round(float(20 * np.log10((np.percentile(env, 95) + 1e-6) / (np.percentile(env, 20) + 1e-6))), 1)
        print(f"  {f}: {e['bpm']} bpm, level {e['level_db']} dB, loud-to-quiet {e['swing_db']} dB")
    json.dump(tr, open(TRACKS, "w"), indent=1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        scan()
    elif len(sys.argv) > 2 and sys.argv[1] == "pick":
        print(pick(sys.argv[2], (sys.argv[3].split(",") if len(sys.argv) > 3 else ()),
                   (sys.argv[4].split(",") if len(sys.argv) > 4 else ())))
    else:
        raise SystemExit(__doc__)
