"""Build the Rhythm Trail narration sprite (Band A).

Voice = "fun kids cartoon robot friend" (owner spec 2026-07-17):
  ENGINE 'edge' (default): Microsoft Edge neural TTS, en-GB-MaisieNeural (a
  British child voice) pitched up a touch, then a light electronic sparkle
  (tremolo + soft drive) so it reads as a friendly robot without hurting
  intelligibility (research: 5-8s comprehend degraded speech worse — keep
  ROBOT_FX subtle; set tremolo_depth 0 to disable entirely).
  ENGINE 'sapi': the old offline Windows SAPI fallback (flat; placeholder only).
  Needs: pip install edge-tts imageio-ffmpeg numpy  (edge engine is online).

A clip key present in tools/narration_overrides/<key>.wav (22050/16-bit/mono)
is used verbatim instead of TTS — the human-voice upgrade path.

Pipeline: per-clip TTS -> 22050 Hz mono WAV -> robotize -> trim -> concatenate
(0.5 s silent head = the iOS <audio> unlock segment, 0.3 s gaps) -> MP3 sprite
public/samples/lessons_a.mp3 -> patch public/js/lessons-data.js (NARR offsets
+ SPRITE name).

Run from the repo root:  python tools/install_lesson_narration.py [--engine sapi]
"""
import asyncio
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
SAMPLES = os.path.join(PUB, "samples")
DATA_JS = os.path.join(PUB, "js", "lessons-data.js")
OVERRIDES = os.path.join(ROOT, "tools", "narration_overrides")

RATE = 22050
HEAD_SILENCE_S = 0.5   # iOS unlock segment at offset 0
GAP_S = 0.3

EDGE_VOICE = "en-GB-MaisieNeural"   # British child voice
EDGE_RATE = "+4%"
EDGE_PITCH = "+15Hz"
# The robot flavour lever. Subtle by design; tremolo_depth 0 = clean voice.
ROBOT_FX = {"tremolo_hz": 27.0, "tremolo_depth": 0.22, "drive": 1.25}

# key -> (spoken text, display text). Chant clips are duration-voiced: the
# syllable is physically held for its length (the channel that teaches duration).
CLIPS = {
    "g_hi":        ("Hi! I'm Beat! Let's make music!", "Hi! I'm Beat!"),
    "g_watch":     ("Watch me!", "Watch me!"),
    "g_turn":      ("Your turn!", "Your turn!"),
    "g_press":     ("Press play to hear it!", "Press play! ▶"),
    "g_yay1":      ("Yes! You did it!", "You did it! 🎉"),
    "g_yay2":      ("Woo hoo! Amazing!", "Amazing! 🎉"),
    "g_yay3":      ("That sounds great!", "Sounds great! 🎉"),
    "g_try":       ("Not quite. Try again!", "Try again!"),
    "g_listen":    ("Listen one more time.", "Listen again… 👂"),
    "g_shift":     ("Right pattern! Try starting on the first heartbeat.", "Start on the first ❤!"),
    "g_ghost":     ("Put notes on the sparkly squares!", "Fill the sparkly squares!"),
    "g_help":      ("I'll show you!", "I'll show you!"),
    "a1_intro":    ("Listen! Can you hear the heartbeat?", "Listen… the heartbeat! ❤"),
    "a1_freeze":   ("Dance with the beat! When it stops, freeze!", "Dance! Then… FREEZE!"),
    "a1_frozen":   ("Freeze!", "FREEZE! 🥶"),
    "a1_touch":    ("Tap a square! Give the heartbeat a sound!", "Tap a square!"),
    "a1_great":    ("You made music on the heartbeat!", "You made music! 🎵"),
    "a2_touch":    ("This note is walking. Add another walking note!", "Add a walking note!"),
    "a2_demo":     ("Four walking notes!", "Four walking notes!"),
    "a2_which":    ("Which one did you hear? Tap it!", "Which one? Tap it!"),
    "a2_copy":     ("Build what you heard!", "Build what you heard!"),
    "a2_gap":      ("Some notes are missing! Fill the gaps!", "Fill the gaps!"),
    "a2_create":   ("Make your own walking pattern!", "Make YOUR pattern!"),
    "a3_touch":    ("A new tool! Running notes! Try one!", "Running notes! Try one!"),
    "a3_demo":     ("Walking, walking, running, walking!", "Walk, walk, run, walk!"),
    "a3_which":    ("Which one did you hear? Tap it!", "Which one? Tap it!"),
    "a3_copy":     ("Build what you heard!", "Build what you heard!"),
    "a3_gap":      ("Fill the gaps with the right notes!", "Fill the gaps!"),
    "a3_create":   ("Make a pattern with running notes!", "Use running notes!"),
    "a4_touch":    ("Take one note away. Make a quiet beat!", "Make a quiet beat!"),
    "a4_demo":     ("Tah, tah, shh, tah! The quiet beat!", "ta ta 🤫 ta"),
    "a4_which":    ("Which one has the quiet beat?", "Which has the quiet beat?"),
    "a4_copy":     ("Build it! Keep the quiet beat quiet!", "Keep the quiet beat quiet!"),
    "a4_rest":     ("Shh! That beat wants to stay quiet!", "Shh! Keep it quiet! 🤫"),
    "a4_create":   ("Make a pattern with a quiet beat!", "Use a quiet beat!"),
    "a5_touch":    ("Two sounds now! Add one more note!", "Two sounds! Add one more!"),
    "a5_which":    ("Which one did you hear? Tap it!", "Which one? Tap it!"),
    "a5_copy":     ("Build the pattern with both sounds!", "Both sounds!"),
    "a5_create":   ("Make your best pattern ever!", "Your best pattern ever!"),
    "a5_reveal":   ("Look! You wrote real music!", "You wrote REAL music! 🎼"),
    "a5_done":     ("You finished! You're a real musician!", "You're a musician! ⭐"),
    "chant_tttt":  ("tah. tah. tah. tah.", "ta ta ta ta"),
    "chant_tatiti":("tah. tah. tee tee. tah.", "ta ta ti-ti ta"),
    "chant_rest":  ("tah. tah. shh. tah.", "ta ta 🤫 ta"),
    "chant_titi":  ("tee tee!", "ti-ti!"),
}


def ffmpeg_exe():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def tts_edge(outdir):
    """Per-clip MP3 from the Edge neural voice, decoded to 22050/mono WAV."""
    import edge_tts
    ff = ffmpeg_exe()

    async def gen(key, text, mp3):
        await edge_tts.Communicate(text, EDGE_VOICE, rate=EDGE_RATE, pitch=EDGE_PITCH).save(mp3)

    for key, (spoken, _d) in CLIPS.items():
        mp3 = os.path.join(outdir, key + ".mp3")
        for attempt in range(3):
            try:
                asyncio.run(gen(key, spoken, mp3))
                break
            except Exception as e:
                if attempt == 2:
                    raise
                print(f"  {key}: retry {attempt + 1} ({e})")
        wav = os.path.join(outdir, key + ".wav")
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", mp3,
                        "-ar", str(RATE), "-ac", "1", "-sample_fmt", "s16", wav], check=True)
    print(f"edge-tts: {len(CLIPS)} clips as {EDGE_VOICE} rate={EDGE_RATE} pitch={EDGE_PITCH}")


def tts_sapi(outdir):
    """Offline Windows SAPI fallback (flat placeholder voice)."""
    manifest = os.path.join(outdir, "clips.json")
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump({k: v[0] for k, v in CLIPS.items()}, f)
    ps = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice = $synth.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'en-GB' } | Select-Object -First 1
if ($voice) { $synth.SelectVoice($voice.VoiceInfo.Name) }
Write-Host ("VOICE: " + $synth.Voice.Name)
$synth.Rate = -1
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(%RATE%, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$clips = Get-Content -Raw '%MANIFEST%' | ConvertFrom-Json
foreach ($p in $clips.PSObject.Properties) {
  $out = Join-Path '%OUTDIR%' ($p.Name + '.wav')
  $synth.SetOutputToWaveFile($out, $fmt)
  $synth.Speak($p.Value)
}
$synth.SetOutputToNull()
$synth.Dispose()
"""
    ps = ps.replace("%RATE%", str(RATE)).replace("%MANIFEST%", manifest).replace("%OUTDIR%", outdir)
    script = os.path.join(outdir, "tts.ps1")
    with open(script, "w", encoding="utf-8-sig") as f:
        f.write(ps)
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script], check=True)


def read_clip(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == RATE and w.getnchannels() == 1 and w.getsampwidth() == 2, \
            f"{path}: expected {RATE} Hz 16-bit mono, got {w.getframerate()}/{w.getnchannels()}ch/{w.getsampwidth()*8}bit"
        return w.readframes(w.getnframes())


def robotize(frames):
    """Light electronic sparkle: slow tremolo + soft drive + edge fades."""
    import numpy as np
    if not ROBOT_FX.get("tremolo_depth"):
        return frames
    x = np.frombuffer(frames, dtype=np.int16).astype(np.float64) / 32768.0
    t = np.arange(len(x)) / RATE
    depth = ROBOT_FX["tremolo_depth"]
    x = x * (1.0 - depth / 2 + (depth / 2) * np.sin(2 * np.pi * ROBOT_FX["tremolo_hz"] * t))
    d = ROBOT_FX["drive"]
    x = np.tanh(d * x) / np.tanh(d)
    fade = int(0.005 * RATE)
    if len(x) > 2 * fade:
        x[:fade] *= np.linspace(0, 1, fade)
        x[-fade:] *= np.linspace(1, 0, fade)
    peak = np.max(np.abs(x)) or 1.0
    x = x * (0.88 / peak if peak > 0.88 else 1.0)
    return (x * 32767).astype(np.int16).tobytes()


def trim_silence(frames, thresh=350):
    """Trim leading/trailing dead air so offsets are tight."""
    n = len(frames) // 2
    vals = struct.unpack(f"<{n}h", frames)
    start, end = 0, n
    while start < n and abs(vals[start]) < thresh: start += 1
    while end > start and abs(vals[end - 1]) < thresh: end -= 1
    pad = int(0.04 * RATE)  # keep 40 ms of breath either side
    start = max(0, start - pad)
    end = min(n, end + pad)
    return struct.pack(f"<{end-start}h", *vals[start:end])


def main():
    engine = "sapi" if "--engine" in sys.argv and "sapi" in sys.argv else "edge"
    os.makedirs(SAMPLES, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="kidseq_narr_")
    print(f"TTS ({engine}) -> {tmp}")
    if engine == "edge":
        try:
            tts_edge(tmp)
        except Exception as e:
            print(f"edge engine failed ({e}); falling back to SAPI")
            engine = "sapi"
            tts_sapi(tmp)
    else:
        tts_sapi(tmp)

    silence = lambda s: b"\x00" * (2 * int(s * RATE))
    parts = [silence(HEAD_SILENCE_S)]
    offsets = {}
    cursor = HEAD_SILENCE_S
    for key, (_spoken, display) in CLIPS.items():
        override = os.path.join(OVERRIDES, key + ".wav")
        if os.path.exists(override):
            frames = trim_silence(read_clip(override))
            print(f"  {key}: HUMAN override")
        else:
            frames = trim_silence(robotize(read_clip(os.path.join(tmp, key + ".wav"))))
        dur = len(frames) / 2 / RATE
        offsets[key] = [round(cursor, 3), round(dur, 3), display]
        parts.append(frames)
        parts.append(silence(GAP_S))
        cursor += dur + GAP_S
    sprite_wav = os.path.join(tmp, "lessons_a_sprite.wav")
    with wave.open(sprite_wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(b"".join(parts))

    mp3 = os.path.join(SAMPLES, "lessons_a.mp3")
    subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", sprite_wav,
                    "-codec:a", "libmp3lame", "-b:a", "64k", "-ac", "1", mp3], check=True)
    old_wav = os.path.join(SAMPLES, "lessons_a.wav")
    if os.path.exists(old_wav):
        os.remove(old_wav)
    ship = "samples/lessons_a.mp3"
    print(f"sprite: {mp3} ({os.path.getsize(mp3)/1e6:.2f} MB, {cursor:.1f}s, {len(CLIPS)} clips, engine={engine})")

    with open(DATA_JS, "r", encoding="utf-8") as f:
        js = f.read()
    narr_json = json.dumps(offsets, ensure_ascii=False, separators=(",", ":"))
    js = re.sub(r"/\*NARR_A_START\*/.*?/\*NARR_A_END\*/",
                f"/*NARR_A_START*/ {narr_json} /*NARR_A_END*/", js, flags=re.S)
    js = re.sub(r'SPRITE:\s*"[^"]*",\s*// NARR_SPRITE',
                f'SPRITE: "{ship}", // NARR_SPRITE', js)
    with open(DATA_JS, "w", encoding="utf-8") as f:
        f.write(js)
    print(f"patched {DATA_JS} (SPRITE={ship})")


if __name__ == "__main__":
    main()
