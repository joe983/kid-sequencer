"""Build the Rhythm Trail narration sprite (Band A).

MVP clips are Windows SAPI TTS placeholders (en-GB voice preferred) — the design
doc flags that real 5-8s comprehend TTS measurably worse, so the ~15 load-bearing
Band A clips should be re-recorded with a human voice before any kid test. This
script keeps the CLIP KEYS stable so swapping in human recordings later is just
"drop WAVs in the override folder and re-run".

Pipeline:
  1. Per-clip WAV via PowerShell System.Speech (22050 Hz, 16-bit, mono).
     A clip key present in tools/narration_overrides/<key>.wav is used verbatim
     (resampled check only) instead of TTS — the human-voice upgrade path.
  2. Concatenate: 0.5 s silent head (the iOS <audio> unlock segment) + clips
     separated by 0.3 s gaps -> public/samples/lessons_a.wav.
  3. If ffmpeg is on PATH, transcode to lessons_a.mp3 (64k mono) and ship that.
  4. Patch public/js/lessons-data.js: the NARR block gets {key: [off, dur, text]}
     and the SPRITE line gets the shipped filename.

Run from the repo root (or this worktree root):  python tools/install_lesson_narration.py
"""
import json
import os
import re
import shutil
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
    "a4_demo":     ("Ta, ta, shh, ta! The quiet beat!", "ta ta 🤫 ta"),
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
    "chant_tttt":  ("taa. taa. taa. taa.", "ta ta ta ta"),
    "chant_tatiti":("taa. taa. tee tee. taa.", "ta ta ti-ti ta"),
    "chant_rest":  ("taa. taa. shh. taa.", "ta ta 🤫 ta"),
    "chant_titi":  ("tee tee!", "ti-ti!"),
}


def tts_generate(outdir):
    """One PowerShell process renders every clip (fast, consistent voice)."""
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


def trim_silence(frames, thresh=350):
    """Trim SAPI's leading/trailing dead air so offsets are tight."""
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
    os.makedirs(SAMPLES, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="kidseq_narr_")
    print(f"TTS -> {tmp}")
    tts_generate(tmp)

    silence = lambda s: b"\x00" * (2 * int(s * RATE))
    parts = [silence(HEAD_SILENCE_S)]
    offsets = {}
    cursor = HEAD_SILENCE_S
    for key, (_spoken, display) in CLIPS.items():
        override = os.path.join(OVERRIDES, key + ".wav")
        src = override if os.path.exists(override) else os.path.join(tmp, key + ".wav")
        frames = trim_silence(read_clip(src))
        dur = len(frames) / 2 / RATE
        offsets[key] = [round(cursor, 3), round(dur, 3), display]
        parts.append(frames)
        parts.append(silence(GAP_S))
        cursor += dur + GAP_S
        if src == override:
            print(f"  {key}: HUMAN override ({dur:.2f}s)")
    sprite_wav = os.path.join(SAMPLES, "lessons_a.wav")
    with wave.open(sprite_wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(b"".join(parts))
    total = os.path.getsize(sprite_wav)
    print(f"sprite: {sprite_wav} ({total/1e6:.2f} MB, {cursor:.1f}s, {len(CLIPS)} clips)")

    ship = "samples/lessons_a.wav"
    if shutil.which("ffmpeg"):
        mp3 = os.path.join(SAMPLES, "lessons_a.mp3")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", sprite_wav,
                        "-codec:a", "libmp3lame", "-b:a", "64k", "-ac", "1", mp3], check=True)
        os.remove(sprite_wav)
        ship = "samples/lessons_a.mp3"
        print(f"mp3: {mp3} ({os.path.getsize(mp3)/1e6:.2f} MB)")
    else:
        print("ffmpeg not found - shipping WAV")

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
