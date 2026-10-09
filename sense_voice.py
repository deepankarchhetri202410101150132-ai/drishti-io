"""Real mic voice detection (librosa + numpy, numpy fallback). V = scream, H = help words."""
import time, threading
import numpy as np
import config
SR = 16000
_state = {"label": "normal", "t": 0, "words": 0, "wt": 0, "rms": 0.0}
def features(y):
    rms = float(np.sqrt(np.mean(y ** 2)))
    try:
        import librosa
        cen = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=SR)))
        f0 = librosa.yin(y, fmin=80, fmax=1000, sr=SR)
        f0 = float(np.median(f0))
    except Exception:
        sp = np.abs(np.fft.rfft(y)); fr = np.fft.rfftfreq(len(y), 1 / SR)
        cen = float((sp * fr).sum() / (sp.sum() + 1e-9))
        f0 = float(fr[np.argmax(sp[1:]) + 1]) if len(sp) > 1 else 0.0
    return rms, cen, f0
def classify(rms, cen, f0):
    if rms >= config.SCREAM_RMS and (cen >= config.SCREAM_CENTROID or f0 >= config.SCREAM_F0): return "scream"
    if rms >= config.SHOUT_RMS: return "shout"
    return "normal"
def _set(label):
    if label != "normal": _state.update(label=label, t=time.time())
def on_key(ch):
    k = config.KEYMAP.get(ch.lower())
    if k == "scream": _set("scream"); print("voice: scream")
    if k == "help": _state.update(words=config.DISTRESS_WORD_SCORES["help"], wt=time.time()); print("voice: help words")
def score():
    decay = lambda t: max(0.0, 1 - (time.time() - t) / config.VOICE_DECAY_SECONDS)
    base = {"scream": 80, "shout": 40}.get(_state["label"], 0) * decay(_state["t"])
    return min(100, base + _state["words"] * decay(_state["wt"]))
def start_mic():
    try:
        import sounddevice as sd
    except Exception as e:
        print("Mic unavailable:", e); return
    def loop():
        while True:
            try:
                y = sd.rec(SR, samplerate=SR, channels=1, dtype="float32"); sd.wait()
                y = y[:, 0]; r, c, f = features(y); _state["rms"] = r; _set(classify(r, c, f))
            except Exception as e:
                print("Mic error:", e); time.sleep(5)
    threading.Thread(target=loop, daemon=True).start()