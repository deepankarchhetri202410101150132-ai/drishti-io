"""Fuses motion + voice into a 0-100 danger score."""
import time
import config
_high_since = [None]
def fuse(motion, voice):
    score = max(motion, voice) * 0.75 + min(motion, voice) * 0.5
    score = int(min(100, score))
    return score, confirmed(score)
def confirmed(score):
    """True only when score stays above the trigger for CONFIRM_SECONDS."""
    if score < config.DANGER_TRIGGER:
        _high_since[0] = None; return False
    _high_since[0] = _high_since[0] or time.time()
    return time.time() - _high_since[0] >= config.CONFIRM_SECONDS
def level(score):
    return "danger" if score >= config.DANGER_TRIGGER else "caution" if score >= config.DANGER_CAUTION else "safe"