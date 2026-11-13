#!/usr/bin/env python3
"""THE SOUND UNDER AN EPISODE (13 Nov 2026): a music bed, a whoosh on every picture change, a
low hit on the loud words, a rise into the payoff.

Kamay, 13 Nov, on the competitor's best reels: "captions and hooks and video movies images
effects and colors and also music, it ALL reflects and is in congruence with each word and
movement Kevin makes." Measured on five of those reels: the quietest moments sit at -22 to
-29 dB where clean speech sits near -50 - every one carries music under his voice the whole
way, and effects on the cuts. Ours had the bare voice.

Everything here is MADE, not downloaded: no licence, no attribution, no takedown, the same on
every platform. A slow four-chord pad in D minor (Dm - Bb - F - C), filtered noise for the
whooshes, a falling sine for the hits.

    make(dur, cuts, hits, path, rise_at=None, seed=7) -> path (48 kHz stereo WAV)
"""
import wave

import numpy as np

SR = 48000
_A4 = 440.0
_n = lambda semis: _A4 * 2 ** (semis / 12.0)          # semitones from A4
# i - VI - III - VII in D minor, low and open (root, fifth, octave, third, fifth)
CHORDS = [
    [-31, -24, -19, -16, -12],     # Dm : D2 A2 D3 F3 A3
    [-35, -28, -23, -19, -16],     # Bb : Bb1 F2 Bb2 D3 F3
    [-28, -21, -16, -12, -9],      # F  : F2 C3 F3 A3 C4
    [-33, -26, -21, -17, -14],     # C  : C2 G2 C3 E3 G3
]
BAR = 6.0


def _db(x):
    return 10 ** (x / 20.0)


def _tone(freq, n, rng, harm=6, roll=1.7):
    """One soft voice: three slightly detuned stacks of a few harmonics, drifting in level."""
    t = np.arange(n) / SR
    out = np.zeros(n)
    for det in (-0.06, 0.0, 0.07):
        f = freq * 2 ** (det / 12.0)
        ph = rng.uniform(0, 6.28)
        for h in range(1, harm + 1):
            if f * h > 5000:
                break
            out += np.sin(2 * np.pi * f * h * t + ph * h) / (h ** roll)
    lfo = 0.8 + 0.2 * np.sin(2 * np.pi * rng.uniform(0.07, 0.16) * t + rng.uniform(0, 6.28))
    return out * lfo / 3.0


def _reverb(x, rng, secs=2.4, wet=0.35):
    n = int(secs * SR)
    ir = rng.normal(0, 1, n) * np.exp(-np.arange(n) / (secs * SR / 5.5))
    ir[:int(0.012 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum())
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:len(x)]
    return x * (1 - wet) + y * wet


def _bed(dur, rng, rise_at):
    n = int(dur * SR)
    L, R = np.zeros(n), np.zeros(n)
    nb = int(BAR * SR)
    xf = int(1.2 * SR)
    k = 0
    while k * nb < n:
        seg = min(nb + xf, n - k * nb)
        env = np.ones(seg)
        f_ = min(xf, seg)
        env[:f_] = np.sin(np.linspace(0, np.pi / 2, f_)) ** 2
        if seg > nb:
            env[nb:] = np.cos(np.linspace(0, np.pi / 2, seg - nb)) ** 2
        for j, semis in enumerate(CHORDS[k % len(CHORDS)]):
            v = _tone(_n(semis), seg, rng) * env * (1.0 if j else 1.25)
            pan = 0.5 + 0.32 * np.sin(j * 1.9 + k)
            L[k * nb:k * nb + seg] += v * (1 - pan)
            R[k * nb:k * nb + seg] += v * pan
        k += 1
    t = np.arange(n) / SR
    swell = 0.82 + 0.18 * np.sin(2 * np.pi * t / (BAR * 2) - 1.2)        # it breathes over two bars
    if rise_at is not None and rise_at < dur:                             # and lifts for the payoff
        swell *= 1.0 + 0.45 * np.clip((t - rise_at) / 3.0, 0, 1)
    fade = np.clip(t / 0.6, 0, 1) * np.clip((dur - t) / 1.2, 0, 1)
    L, R = _reverb(L * swell * fade, rng), _reverb(R * swell * fade, rng)
    return L, R


def _whoosh(rng, secs=0.55):
    n = int(secs * SR)
    x = rng.normal(0, 1, n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X *= np.exp(-((np.log2(np.maximum(f, 20) / 1400.0)) ** 2) / 1.6)       # a band around 1.4 kHz
    x = np.fft.irfft(X, n)
    t = np.linspace(0, 1, n)
    env = np.exp(-((t - 0.62) / 0.2) ** 2)                                 # swells, peaks, falls off fast
    x = x * env
    return x / (np.abs(x).max() + 1e-9)


def _hit(secs=0.9):
    n = int(secs * SR)
    t = np.arange(n) / SR
    f = 42 + 60 * np.exp(-t * 9)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.2)
    x[:int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    return x / (np.abs(x).max() + 1e-9)


def _riser(rng, secs=2.2):
    n = int(secs * SR)
    t = np.linspace(0, 1, n)
    x = rng.normal(0, 1, n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X *= np.exp(-((np.log2(np.maximum(f, 20) / 2600.0)) ** 2) / 2.2)
    x = np.fft.irfft(X, n) * t ** 2.4
    tone = np.sin(2 * np.pi * np.cumsum(180 + 420 * t ** 2) / SR) * t ** 3 * 0.25
    x = x / (np.abs(x).max() + 1e-9) + tone
    return x / (np.abs(x).max() + 1e-9)


def _add(buf, x, at, gain, peak_frac=0.0):
    i = int(at * SR) - int(len(x) * peak_frac)
    a, b = max(0, i), min(len(buf), i + len(x))
    if b > a:
        buf[a:b] += x[a - i:b - i] * gain


def make(dur, cuts, hits, path, rise_at=None, seed=7, bed_db=-27.0, fx_db=-19.0):
    """dur seconds; cuts = picture changes (a whoosh peaks on each); hits = the loud words.

    bed_db: the music's level against full scale (his voice is mixed near -16; the reference
    reels keep music about 8-14 dB under him). fx_db: the peak of a whoosh; hits sit 3 dB over.
    """
    rng = np.random.default_rng(seed)
    L, R = _bed(dur, rng, rise_at)
    rms = np.sqrt(((L ** 2 + R ** 2) / 2).mean()) + 1e-9
    g = _db(bed_db) / rms
    L, R = L * g, R * g
    n = len(L)
    fxl, fxr = np.zeros(n), np.zeros(n)
    w, h = _whoosh(rng), _hit()
    last = -9.0
    for i, c in enumerate(sorted(cuts)):
        if c < 0.15 or c - last < 0.7:               # never two on top of each other
            continue
        last = c
        side = 0.35 if i % 2 else 0.65
        _add(fxl, w, c, _db(fx_db) * (1 - side) * 2, 0.62)
        _add(fxr, w, c, _db(fx_db) * side * 2, 0.62)
    last = -9.0
    for c in sorted(hits):
        if c - last < 1.1:
            continue
        last = c
        _add(fxl, h, c, _db(fx_db + 3))
        _add(fxr, h, c, _db(fx_db + 3))
    if rise_at is not None and rise_at > 2.4:
        r = _riser(rng)
        _add(fxl, r, rise_at, _db(fx_db - 1), 1.0)
        _add(fxr, r, rise_at, _db(fx_db - 1), 1.0)
        _add(fxl, h, rise_at, _db(fx_db + 5))
        _add(fxr, h, rise_at, _db(fx_db + 5))
    fxl, fxr = _reverb(fxl, rng, 1.2, 0.18), _reverb(fxr, rng, 1.2, 0.18)
    out = np.stack([L + fxl, R + fxr], 1)
    out = np.tanh(out * 1.0)                         # a soft ceiling, never a hard clip
    pcm = (np.clip(out, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as fh:
        fh.setnchannels(2); fh.setsampwidth(2); fh.setframerate(SR)
        fh.writeframes(pcm.tobytes())
    return path


if __name__ == "__main__":
    import sys
    p = make(float(sys.argv[1]) if len(sys.argv) > 1 else 46.0, [3.3, 6.9, 8.1, 9.6, 13.2, 16.8, 24.3, 27.9, 28.7],
             [15.6, 26.1], sys.argv[2] if len(sys.argv) > 2 else "/tmp/episode_sound.wav", rise_at=33.0)
    print(p)
