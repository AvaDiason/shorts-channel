"""Usage: python3 tts_gen.py <episode_dir> <models_dir>
Reads <episode_dir>/script.py (PHRASES = [(text, pause_after_s, speed, gain_db), ...]),
writes <episode_dir>/voice_raw.wav and <episode_dir>/timing.json."""
import json, sys, importlib.util, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
ep, models = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("script", f"{ep}/script.py"); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
k = Kokoro(f"{models}/kokoro-v1.0.int8.onnx", f"{models}/voices-v1.0.bin")
style = 0.8 * k.get_voice_style("bm_george") + 0.2 * k.get_voice_style("bm_fable")   # house narrator voice
sr = 24000; out = [np.zeros(int(0.35 * sr), np.float32)]; t = 0.35; timing = []
for text, pause, sp, gdb in mod.PHRASES:
    a, sr = k.create(text, voice=style, speed=sp, lang="en-gb")
    a = a.astype(np.float32); idx = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, idx[0] - 240):idx[-1] + 600]; a *= 10 ** (gdb / 20)
    timing.append({"text": text, "start": t, "end": t + len(a) / sr}); out.append(a); t += len(a) / sr
    out.append(np.zeros(int(pause * sr), np.float32)); t += pause
y = np.concatenate(out); y = y / np.abs(y).max() * 0.9
sf.write(f"{ep}/voice_raw.wav", y, sr); json.dump(timing, open(f"{ep}/timing.json", "w"), indent=1)
print("total", round(t, 2))
for i, p in enumerate(timing): print(i, round(p["start"], 1), p["text"][:40])
