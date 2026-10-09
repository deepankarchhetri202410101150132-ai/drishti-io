"""Local Ollama chatbot with offline rule-based fallback."""
import json, time, urllib.request
import config, monitor
def ask(question, context=None):
    n = monitor.density(); h = time.localtime().tm_hour; night = h >= 21 or h < 5
    ctx = f"Helpers within 300m: {n}. Nearest: {monitor.nearest()}. Hour: {h}. Night: {night}."
    prompt = f"You are दृष्टि-IO (Drishti-IO), a calm safety friend. Answer in 2 short sentences. Context: {ctx}\nUser: {question}"
    try:
        req = urllib.request.Request(config.OLLAMA_URL, json.dumps({"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False}).encode(), {"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=20).read())["response"].strip()
    except Exception:
        q = question.lower()
        if "helper" in q or "nearby" in q: return f"{n} helpers are within 300m."
        if "route" in q: return "Stay on lit, busy roads. " + ("It's late, so share your location." if night else "Daylight helps.")
        if "safe" in q: return f"{n} helpers are around you. " + ("It's night, so stay alert." if night else "It looks fine.")
        return "I'm here. Ask about safety, helpers or routes."