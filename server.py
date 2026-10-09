"""दृष्टि-IO server: Flask, queue-based SOS delivery, 10-second confirmation window. No popups."""
import json, logging, os, threading, time
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

BASE = os.path.dirname(os.path.abspath(__file__))
EVENTS_FILE = os.path.join(BASE, "events.json")
try:
    import config
except Exception:
    config = None
cfg = lambda name, default: getattr(config, name, default) if config else default
SIM_DISTANCE_M = cfg("SIMULATED_DISTANCE_M", 50)
DANGER_TRIGGER = cfg("DANGER_TRIGGER", 50)
COUNTDOWN_SECONDS = cfg("COUNTDOWN_SECONDS", 10)
COOLDOWN_SECONDS = 30

app = Flask(__name__, static_folder=BASE, static_url_path="/static")
CORS(app)
lock = threading.RLock()       # guards `state` (re-entrant, so nested use cannot deadlock)
file_lock = threading.Lock()   # guards events.json only, so file I/O never blocks polling
state = {"motion": 0, "voice": 0, "danger": 0, "last_sensor": 0, "last_auto": 0,
         "seq": 0, "pid": 0, "sos": None, "pending": None, "sos_log": []}
devices = {}


# ---------- persistent event log ----------
def load_events():
    try:
        with open(EVENTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def log_event(kind, msg, **extra):
    ev = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "epoch": time.time(), "kind": kind, "msg": msg, **extra}
    with file_lock:
        events = load_events()[-499:] + [ev]
        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=1)
    return ev


# ---------- SOS queue ----------
def raise_alert(source, note="", cid=None, device=None):
    """Every SOS gets its own sequence number and stays in sos_log. Nothing is overwritten."""
    msg = f"SOS from {source}. {note}".strip()
    log_event("sos", msg, source=source, distance_m=SIM_DISTANCE_M)
    with lock:
        state["seq"] += 1
        sos = {"id": state["seq"], "active": True, "from": cid,
               "device": (device or source or "").lower().replace(" sensors", ""),
               "msg": msg, "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
               "distance_m": SIM_DISTANCE_M, "direction": "northeast", "responded": False}
        state["sos"] = sos
        state["sos_log"] = (state["sos_log"] + [dict(sos)])[-300:]
        if state["pending"]:
            state["pending"]["active"] = False
    return sos

def reset_sensors():
    try:
        import sense_motion, sense_voice
        sense_motion._last.update(kind=None, t=0)
        sense_voice._state.update(label="normal", t=0, words=0, wt=0)
    except Exception:
        pass

def start_pending(reason, cid=None, device="laptop"):
    """Danger detected: give the user COUNTDOWN_SECONDS to say they are safe. Fires SOS if they don't."""
    with lock:
        if (state["sos"] and state["sos"]["active"]) or (state["pending"] and state["pending"]["active"]):
            return None
        if time.time() - state["last_auto"] < COOLDOWN_SECONDS:
            return None
        state["pid"] += 1
        state["last_auto"] = time.time()
        state["pending"] = {"id": state["pid"], "active": True, "from": cid, "device": device,
                            "reason": reason, "deadline": time.time() + COUNTDOWN_SECONDS}
    log_event("detect", f"Danger detected ({reason}). Waiting {COUNTDOWN_SECONDS}s for confirmation.")

def pending_watcher():
    while True:
        time.sleep(0.1)
        fire = None
        with lock:
            p = state["pending"]
            if p and p["active"] and time.time() >= p["deadline"]:
                p["active"] = False
                fire = dict(p)
        if fire:
            raise_alert(f"{fire['device']} sensors", "Sent automatically after the countdown.", fire["from"], fire["device"])

def danger_from(motion, voice):
    try:
        import decide
        r = decide.fuse(motion, voice)
        return int(r[0] if isinstance(r, (tuple, list)) else r)
    except Exception:
        return int(min(100, max(motion, voice) * 0.75 + min(motion, voice) * 0.5))


# ---------- pages ----------
@app.route("/")
def landing():
    return send_from_directory(BASE, "index.html")

@app.route("/dashboard")
def dashboard():
    return send_from_directory(BASE, "dashboard.html")

@app.route("/mic.js")
def mic_js():
    return send_from_directory(BASE, "mic.js")

@app.route("/alarm.js")
def alarm_js():
    return send_from_directory(BASE, "alarm.js")

@app.errorhandler(404)
def not_found(_):
    html = ("<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'><title>Lost? - दृष्टि-IO</title>"
            "<body style='margin:0;min-height:100vh;display:grid;place-items:center;background:#0a0e1a;color:#e5e7eb;"
            "font-family:system-ui,sans-serif;text-align:center'><div><h1 style='font-size:48px;margin:0 0 8px'>Lost? Let's get you back.</h1>"
            "<p style='color:#9ca3af'>That page doesn't exist.</p><a href='/' style='display:inline-block;margin-top:16px;"
            "padding:12px 24px;border-radius:8px;background:#7c6df2;color:#fff;text-decoration:none;font-weight:600'>Back to दृष्टि-IO</a></div></body>")
    return html, 404


# ---------- API ----------
@app.route("/sos", methods=["POST"])
def sos():
    d = request.get_json(silent=True) or {}
    s = raise_alert(d.get("device", "phone"), d.get("note", ""), d.get("cid"), d.get("device"))
    return jsonify(ok=True, id=s["id"])

@app.route("/sos/cancel", methods=["POST"])
def sos_cancel():
    with lock:
        had = bool((state["sos"] and state["sos"]["active"]) or (state["pending"] and state["pending"]["active"]))
        if state["sos"]: state["sos"]["active"] = False
        if state["pending"]: state["pending"]["active"] = False
        state.update(danger=0, motion=0, voice=0, last_auto=time.time())
    reset_sensors()
    if had:
        log_event("safe", "User marked safe. SOS ended.")
    return jsonify(ok=True)

@app.route("/sos/respond", methods=["POST"])
def sos_respond():
    with lock:
        live = bool(state["sos"] and state["sos"]["active"])
        if live: state["sos"]["responded"] = True
    if live:
        log_event("respond", "A helper is responding.")
    return jsonify(ok=True)

@app.route("/poll")
def poll():
    """Light endpoint, polled every 500 ms. `since` is the last SOS id the client has seen,
    so a lost response is simply re-sent on the next poll. since=-1 means 'first poll'."""
    cid = request.args.get("cid", "")
    try:
        since = int(request.args.get("since", -1))
    except ValueError:
        since = -1
    now = time.time()
    with lock:
        devices[cid] = now
        for k in [k for k, t in devices.items() if now - t > 30]:
            devices.pop(k, None)
        others = sum(1 for c in devices if c != cid)
        events = [] if since < 0 else [e for e in state["sos_log"] if e["id"] > since]
        sos_now = dict(state["sos"]) if state["sos"] else None
        p = state["pending"]
        pend = ({**p, "remaining_ms": max(0, int((p["deadline"] - now) * 1000))} if p and p["active"] else None)
        out = dict(latest=state["seq"], events=events, sos=sos_now, pending=pend, devices=others,
                   danger=state["danger"], motion=state["motion"], voice=state["voice"], now=now)
    return jsonify(out)

@app.route("/sensor-data", methods=["POST"])
def sensor_data():
    d = request.get_json(silent=True) or {}
    motion = float(d.get("motion", d.get("motion_score", 0)))
    voice = float(d.get("voice", d.get("voice_score", state["voice"])))
    danger = danger_from(motion, voice)
    with lock:
        state.update(motion=motion, voice=voice, danger=danger, last_sensor=time.time())
    if danger >= DANGER_TRIGGER:
        start_pending(f"phone sensors, score {danger}", cid=d.get("cid"), device="phone")
    return jsonify(ok=True, danger=danger)

@app.route("/simulate", methods=["POST"])
def simulate():
    import sense_motion, sense_voice
    k = (request.get_json(silent=True) or {}).get("kind", "")
    if k in ("fall", "struggle", "dizzy", "freeze"): sense_motion.trigger(k)
    elif k == "scream": sense_voice._set("scream")
    elif k == "help": sense_voice.on_key("h")
    else: return jsonify(ok=False), 400
    log_event("simulate", f"Simulated {k}")
    return jsonify(ok=True)

@app.route("/events")
def events():
    return jsonify(events=load_events()[-100:])

@app.route("/status")
def status():
    return jsonify(ok=True, danger=state["danger"])

@app.route("/helpers")
def helpers_api():
    import monitor
    return jsonify(helpers=monitor.helpers(), alert=monitor.low_density_alert())

@app.route("/chat", methods=["POST"])
def chat():
    q = (request.get_json(silent=True) or {}).get("message", "")
    try:
        import chatbot
        return jsonify(reply=str(chatbot.ask(q)))
    except Exception:
        return jsonify(reply="The assistant isn't running. Start Ollama and try again.")


# ---------- laptop sensors (keyboard simulation + real mic) ----------
def local_sensing():
    try:
        import sense_motion, sense_voice, decide
    except Exception as e:
        print("Laptop sensing unavailable:", e); return
    sense_voice.start_mic()
    sense_motion.start_keyboard([sense_motion.on_key, sense_voice.on_key])
    while True:
        time.sleep(0.25)
        try:
            m, v = sense_motion.score(), sense_voice.score()
            if time.time() - state["last_sensor"] > 5:
                score, go = decide.fuse(m, v)
                with lock:
                    state.update(motion=m, voice=v, danger=score)
                if go:
                    start_pending(f"laptop sensors, score {score}", None, "laptop")
        except Exception as e:
            print("sensing error:", e)


class _QuietPoll(logging.Filter):
    def filter(self, record):
        return "/poll" not in record.getMessage()


if __name__ == "__main__":
    logging.getLogger("werkzeug").addFilter(_QuietPoll())
    threading.Thread(target=pending_watcher, daemon=True).start()
    threading.Thread(target=local_sensing, daemon=True).start()
    print("दृष्टि-IO: http://localhost:5000  |  dashboard: http://localhost:5000/dashboard  |  phone: http://192.168.1.39:5000")
    app.run(host="0.0.0.0", port=5000, threaded=True)
    