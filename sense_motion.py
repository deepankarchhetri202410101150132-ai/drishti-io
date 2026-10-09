"""Keyboard-simulated motion events: F fall, S struggle, D dizzy, Z freeze."""
import time, threading
import config
_last = {"kind": None, "t": 0}
def trigger(kind):
    _last.update(kind=kind, t=time.time())
def score():
    k = _last["kind"]
    if not k: return 0
    age = time.time() - _last["t"]
    base = config.MOTION_SCORES.get(k, 0)
    return max(0, base * (1 - age / config.VOICE_DECAY_SECONDS))
def on_key(ch):
    kind = config.KEYMAP.get(ch.lower())
    if kind in config.MOTION_SCORES: trigger(kind); print("motion:", kind)
def start_keyboard(handlers):
    """Reads keys on Windows console and sends them to every handler."""
    try:
        import msvcrt
    except ImportError:
        return
    def loop():
        while True:
            try:
                ch = msvcrt.getwch()
                for h in handlers: h(ch)
            except Exception:
                return
    threading.Thread(target=loop, daemon=True).start()
