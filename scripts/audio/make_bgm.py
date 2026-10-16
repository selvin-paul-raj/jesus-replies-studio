#!/usr/bin/env python3
"""Original background music for Jesus Replies (2026-10-16, DEC-JR-007).

Every track in public/audio/bgm-*.mp3 is synthesised here from scratch: warm pads, a soft
bass and a piano-like arpeggio, a simple convolution reverb, then mastered to about
-20 LUFS so the on-screen story stays the focus. No samples, loops or recordings from
anyone else are used, so the output is an original work of this project (see
public/audio/LICENSES.md).

Each track is rendered circularly (the reverb tail is folded back onto the start), so it
loops without a click when an episode is longer than the track.

  pip install numpy scipy && python3 scripts/audio/make_bgm.py      # needs ffmpeg (libmp3lame)
"""
import pathlib, subprocess, sys, tempfile, wave
import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt

SR = 44100
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "public/audio"

NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6,
        "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
MAJOR = [0, 2, 4, 5, 7, 9, 11]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def triad(key, degree, octave=4):
    """Diatonic triad (+ added 9th for warmth) on scale degree 1..7 of a major key."""
    root = 12 * (octave + 1) + NOTE[key]
    idx = [degree - 1, degree + 1, degree + 3, degree + 7]
    out = []
    for i in idx:
        out.append(root + MAJOR[i % 7] + 12 * (i // 7))
    return out


def env(n, attack, release, total):
    e = np.ones(total)
    a, r = int(attack * SR), int(release * SR)
    e[:a] = np.linspace(0, 1, a) ** 2
    e[n:n + r] = np.linspace(1, 0, r) ** 2 if n + r <= total else np.linspace(1, 0, r)[: total - n] ** 2
    e[n + r:] = 0
    return e


def pad_note(f, dur, rng):
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for det in (-0.07, 0.0, 0.06):                       # three slightly detuned voices (cents-ish)
        ff = f * 2 ** (det / 12)
        vib = 0.0015 * np.sin(2 * np.pi * (0.18 + rng.random() * 0.1) * t + rng.random() * 6.28)
        ph = 2 * np.pi * np.cumsum(ff * (1 + vib)) / SR
        out += np.sin(ph) + 0.22 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)
    return out / 3


def piano_note(f, dur):
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for k, amp in enumerate((1.0, 0.45, 0.22, 0.12, 0.06), start=1):
        fk = f * k * (1 + 0.0004 * k * k)                 # slight stretch, like a real string
        out += amp * np.sin(2 * np.pi * fk * t) * np.exp(-t * (1.6 + 0.9 * k))
    attack = np.minimum(1, t / 0.006)
    return out * attack


def reverb_ir(seconds, seed):
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = r.standard_normal((n, 2)) * np.exp(-t * 3.2)[:, None]
    sos = butter(2, 5000, "low", fs=SR, output="sos")
    ir = sosfilt(sos, ir, axis=0)
    return ir / np.sqrt((ir ** 2).sum(axis=0))


def render(spec):
    rng = np.random.default_rng(spec["seed"])
    L, prog, reps = spec["chord_s"], spec["progression"], spec["repeats"]
    total = int(L * len(prog) * reps * SR)
    tail = int(6 * SR)
    buf = np.zeros((total + tail, 2))
    chords = [triad(spec["key"], d, spec.get("octave", 4)) for d in prog] * reps
    for ci, notes in enumerate(chords):
        start = int(ci * L * SR)
        hold = L + 1.6                                       # overlap into the next chord (crossfade)
        n_tot = int((hold + 2.0) * SR)
        e = env(int(hold * SR), 1.4, 2.0, n_tot)
        for j, m in enumerate(notes):
            s = pad_note(hz(m), n_tot / SR, rng) * e * 0.09
            pan = 0.5 + (j - 1.5) * 0.18
            buf[start:start + n_tot, 0] += s * (1 - pan)
            buf[start:start + n_tot, 1] += s * pan
        bass = pad_note(hz(notes[0] - 24), n_tot / SR, rng) * e * 0.10
        buf[start:start + n_tot] += bass[:, None] * 0.5
        # piano arpeggio, sparse and slow
        pattern = spec["arp"]
        step = L / len(pattern)
        for k, p in enumerate(pattern):
            if p is None:
                continue
            m = notes[p % len(notes)] + 12 * (p // len(notes)) + 12 * spec.get("piano_up", 0)
            vel = 0.16 * (0.8 + 0.4 * rng.random())
            s = piano_note(hz(m), 3.5) * vel
            o = start + int((k * step + rng.random() * 0.015) * SR)
            pan = 0.35 + 0.3 * rng.random()
            buf[o:o + len(s), 0] += s * (1 - pan)
            buf[o:o + len(s), 1] += s * pan
    # fold the tail onto the start so the track loops seamlessly
    loop = buf[:total].copy()
    loop[:tail] += buf[total:total + tail]
    # circular reverb: pad with the end, convolve, keep the middle
    ir = reverb_ir(3.0, spec["seed"] + 1)
    ext = np.concatenate([loop[-len(ir):], loop])
    wet = np.stack([fftconvolve(ext[:, c], ir[:, c])[len(ir):len(ir) + total] for c in range(2)], axis=1)
    mix = 0.72 * loop + 0.45 * wet
    sos = butter(2, 7000, "low", fs=SR, output="sos")
    mix = sosfilt(sos, mix, axis=0)
    return mix / (np.abs(mix).max() + 1e-9) * 0.8


TRACKS = [
    {"name": "bgm-01", "title": "Quiet Porch", "key": "D", "progression": [1, 5, 6, 4], "chord_s": 4.0, "repeats": 4,
     "arp": [0, 1, 2, 3, 2, 1, None, None], "seed": 101},
    {"name": "bgm-02", "title": "Morning Light", "key": "G", "progression": [1, 4, 6, 5], "chord_s": 4.5, "repeats": 4,
     "arp": [0, None, 2, None, 3, None, 2, None], "seed": 202},
    {"name": "bgm-03", "title": "Still Waters", "key": "Eb", "progression": [6, 4, 1, 5], "chord_s": 4.25, "repeats": 4,
     "arp": [None, 0, None, 2, None, None, 3, None], "seed": 303},
    {"name": "bgm-04", "title": "Evening Prayer", "key": "C", "progression": [4, 1, 5, 6], "chord_s": 4.0, "repeats": 4,
     "arp": [0, 2, 3, 2, 0, None, None, None], "seed": 404, "octave": 4},
    {"name": "bgm-05", "title": "Held", "key": "F", "progression": [1, 6, 2, 5], "chord_s": 4.5, "repeats": 4,
     "arp": [2, None, 1, None, 0, None, None, None], "seed": 505, "piano_up": 1},
]


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main(only=None):
    OUT.mkdir(parents=True, exist_ok=True)
    for spec in TRACKS:
        if only and spec["name"] not in only:
            continue
        x = render(spec)
        with tempfile.TemporaryDirectory() as td:
            wav = pathlib.Path(td) / "t.wav"
            write_wav(wav, x)
            mp3 = OUT / f"{spec['name']}.mp3"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                            "-af", "loudnorm=I=-20:TP=-3:LRA=7", "-ar", str(SR),
                            "-c:a", "libmp3lame", "-b:a", "160k",
                            "-metadata", f"title={spec['title']}", "-metadata", "artist=Jesus Replies (original)",
                            "-metadata", "copyright=Original work for Jesus Replies, 2026", str(mp3)], check=True)
        print(f"{mp3.relative_to(ROOT)}  {len(x) / SR:.1f}s  {spec['title']}")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
