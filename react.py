"""Siren, police voice, mesh SOS relay."""
import json, threading, urllib.request
import config
def siren(seconds=5):
    def run():
        try:
            import numpy as np, pygame
            pygame.mixer.init(22050, -16, 1)
            t = np.linspace(0, 1, 22050, False)
            wave = (np.sign(np.sin(2 * np.pi * (700 + 300 * np.sin(2 * np.pi * 2 * t)) * t)) * 8000).astype("int16")
            snd = pygame.sound.Sound(buffer=wave.tobytes()); snd.play(loops=seconds - 1)
        except Exception as e:
            print("Siren unavailable:", e)
    threading.Thread(target=run, daemon=True).start()
def police_voice(text="Police are on their way. Stay where you are."):
    def run():
        try:
            import pyttsx3
            e = pyttsx3.init(); e.say(text); e.runAndWait()
        except Exception as ex:
            print("Voice unavailable:", ex)
    threading.Thread(target=run, daemon=True).start()
def mesh_sos(device="mesh"):
    try:
        req = urllib.request.Request("http://localhost:5000/sos", json.dumps({"device": device}).encode(), {"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3)
    except Exception as e:
        open("sms_log.txt", "a").write(f"SMS fallback: SOS ({e})\n")
def help_coming(distance=None):
    return f"Help coming. Nearest helper is {distance or config.SIMULATED_DISTANCE_M}m away."
def trigger_all():
    siren(); police_voice(); mesh_sos()