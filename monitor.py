"""Simulated helpers, density and low-density warnings."""
import config
HELPERS = [{"id": i + 1, "d": d, "dir": n, "angle": a} for i, (d, n, a) in enumerate(
    [(182, "S", 180), (221, "NW", 315), (140, "NE", 45), (260, "E", 90), (95, "SW", 225), (290, "W", 270)])]
def helpers(radius=300):
    return [h for h in HELPERS if h["d"] <= radius]
def density(radius=300):
    return len(helpers(radius))
def nearest():
    hs = helpers(); return min(hs, key=lambda h: h["d"]) if hs else None
def low_density_alert():
    n = density()
    return f"Only {n} helpers nearby. Stay on busier streets." if n < config.LOW_HELPER_THRESHOLD else None