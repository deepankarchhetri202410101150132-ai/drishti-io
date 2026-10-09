"""Location sharing (demo distance is simulated)."""
import time, config
def share(lat=None, lon=None):
    return {"lat": lat, "lon": lon, "distance_m": config.SIMULATED_DISTANCE_M, "ts": time.strftime("%H:%M:%S")}
def context():
    return {"distance_m": config.SIMULATED_DISTANCE_M, "hour": time.localtime().tm_hour}