"""Small audio helpers: buffers, envelopes, WAV I/O (stdlib only + numpy)."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100


def midi_to_hz(m: float) -> float:
    return 440.0 * (2.0 ** ((m - 69) / 12.0))


def seconds_per_beat(tempo: float) -> float:
    return 60.0 / tempo


def adsr(n: int, sr: int, a: float, d: float, s: float, r: float) -> np.ndarray:
    """ADSR envelope of length n samples. a/d/r in seconds, s in 0..1."""
    env = np.zeros(n, dtype=np.float32)
    ai = min(int(a * sr), n)
    di = min(int(d * sr), max(0, n - ai))
    ri = min(int(r * sr), max(0, n - ai - di))
    si = max(0, n - ai - di - ri)
    idx = 0
    if ai:
        env[idx:idx + ai] = np.linspace(0, 1, ai, endpoint=False); idx += ai
    if di:
        env[idx:idx + di] = np.linspace(1, s, di, endpoint=False); idx += di
    if si:
        env[idx:idx + si] = s; idx += si
    if ri:
        env[idx:idx + ri] = np.linspace(s, 0, ri, endpoint=True); idx += ri
    return env


def add_at(buf: np.ndarray, sig: np.ndarray, start: int) -> None:
    """Sum `sig` into `buf` at sample offset `start`, clipping to buf length."""
    if start >= len(buf):
        return
    end = min(len(buf), start + len(sig))
    buf[start:end] += sig[: end - start]


def normalize(buf: np.ndarray, peak: float = 0.9) -> np.ndarray:
    m = float(np.max(np.abs(buf))) if buf.size else 0.0
    return buf * (peak / m) if m > 1e-9 else buf


def to_stereo(mono: np.ndarray) -> np.ndarray:
    return np.stack([mono, mono], axis=1)


def _mono_at_rate(data: np.ndarray, nch: int, sr: int, target_sr: int) -> np.ndarray:
    if nch > 1:
        data = data.reshape(-1, nch).mean(axis=1)
    if sr != target_sr and data.size:
        m = int(round(data.shape[0] / sr * target_sr))
        x_old = np.linspace(0.0, 1.0, data.shape[0], endpoint=False)
        x_new = np.linspace(0.0, 1.0, m, endpoint=False)
        data = np.interp(x_new, x_old, data)
    return data.astype(np.float32)


def read_wav(path: str | Path, target_sr: int = SR) -> np.ndarray:
    """Read an audio file to a mono float32 buffer at `target_sr`.

    Fast path: stdlib `wave` for PCM WAVs (8/16/24/32-bit int). Anything the
    stdlib can't parse (IEEE-float WAVs — common in commercial packs — flac,
    etc.) falls back to pedalboard's AudioFile decoder. Downmixes to mono and
    linearly resamples. Used to load the drum one-shots (render/sample_kit.py).
    """
    path = Path(path)
    try:
        with wave.open(str(path), "rb") as w:
            nch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(n)
        if sw == 1:  # unsigned 8-bit
            data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        elif sw == 2:
            data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        elif sw == 3:  # packed 24-bit little-endian
            b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
            v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
            v = np.where(v & 0x800000, v - 0x1000000, v)
            data = v.astype(np.float32) / 8388608.0
        elif sw == 4:
            data = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
        else:
            raise wave.Error(f"unsupported sample width {sw}")
        return _mono_at_rate(data, nch, sr, target_sr)
    except wave.Error:
        from pedalboard.io import AudioFile  # already an engine dep (mixmaster)

        with AudioFile(str(path)) as f:
            sr = int(f.samplerate)
            audio = f.read(f.frames)  # (channels, frames) float32
        return _mono_at_rate(audio.T.reshape(-1), audio.shape[0], sr, target_sr)


def write_wav(path: str | Path, audio: np.ndarray, sr: int = SR) -> Path:
    """Write float audio (mono 1-D or stereo Nx2) to a 16-bit WAV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    a = audio
    if a.ndim == 1:
        a = to_stereo(a)
    a = np.clip(a, -1.0, 1.0)
    pcm = (a * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(a.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path
