// दृष्टि-IO alarm: Web Audio siren + SpeechSynthesis voice. No external files.
(function () {
  let ctx, master, nodes = [], timer = null, muted = false, active = null, unlocked = false;
  const LEVEL = 0.9, DUCK = 0.22;
  const MSG = {
    victim: "Police are on the way. Stay away from her. Help is coming.",
    helper: "A girl needs your help. Someone nearby is in danger. Please respond."
  };
  const hasSpeech = () => "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
  function ensure() {
    if (!ctx) { const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return null; ctx = new AC(); }
    if (ctx.state === "suspended") ctx.resume().catch(() => {});
    return ctx;
  }
  function unlock() {               // runs on the first tap, keypress or touch
    const c = ensure();
    if (c) { const s = c.createBufferSource(); s.buffer = c.createBuffer(1, 1, 22050); s.connect(c.destination); s.start(0); }
    if (!unlocked && hasSpeech()) {
      unlocked = true;
      try { const u = new SpeechSynthesisUtterance(" "); u.volume = 0; speechSynthesis.speak(u); speechSynthesis.getVoices(); } catch (e) {}
    }
  }
  ["pointerdown", "touchstart", "keydown"].forEach(t => addEventListener(t, unlock, { passive: true }));
  if (hasSpeech()) speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();

  function buildSiren() {
    const c = ensure(); if (!c) return;
    const comp = c.createDynamicsCompressor();
    master = c.createGain(); master.gain.value = 0;
    const a = c.createOscillator(), b = c.createOscillator(), lfo = c.createOscillator();
    a.type = "sawtooth"; b.type = "square"; lfo.type = "triangle";
    a.frequency.value = 900; b.frequency.value = 904; lfo.frequency.value = 0.9;   // wail between ~620 and ~1180 Hz
    const depth = c.createGain(); depth.gain.value = 280;
    lfo.connect(depth); depth.connect(a.frequency); depth.connect(b.frequency);
    const ga = c.createGain(), gb = c.createGain(); ga.gain.value = 0.6; gb.gain.value = 0.3;
    a.connect(ga); b.connect(gb); ga.connect(master); gb.connect(master);
    master.connect(comp); comp.connect(c.destination);
    [a, b, lfo].forEach(n => n.start()); nodes = [a, b, lfo];
    master.gain.setTargetAtTime(muted ? 0 : LEVEL, c.currentTime, 0.05);
  }
  function pickVoice() {
    const v = speechSynthesis.getVoices();
    return v.find(x => /en[-_]IN/i.test(x.lang)) || v.find(x => /en[-_]GB/i.test(x.lang)) || v.find(x => /^en/i.test(x.lang)) || null;
  }
  function level(v) { if (ctx && master && !muted) master.gain.setTargetAtTime(v, ctx.currentTime, 0.15); }
  function speak(role) {
    if (muted || !MSG[role] || !hasSpeech()) return;
    try {
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(MSG[role]), v = pickVoice();
      if (v) { u.voice = v; u.lang = v.lang; } else u.lang = "en-IN";
      u.rate = 0.9; u.pitch = 0.9; u.volume = 1;
      const restore = () => level(LEVEL);
      u.onstart = () => level(DUCK); u.onend = restore; u.onerror = restore;
      setTimeout(restore, 7000);     // never stay ducked if speech stalls
      speechSynthesis.speak(u);
    } catch (e) { /* siren-only fallback */ }
  }
  function stop() {
    clearInterval(timer); timer = null;
    try { if (hasSpeech()) speechSynthesis.cancel(); } catch (e) {}
    if (ctx && master) {
      const m = master, n = nodes;
      m.gain.setTargetAtTime(0, ctx.currentTime, 0.03);
      setTimeout(() => { n.forEach(x => { try { x.stop(); } catch (e) {} }); try { m.disconnect(); } catch (e) {} }, 200);
    }
    nodes = []; master = null; active = null; muted = false;
  }
  function start(role) {
    stop(); active = role; buildSiren();
    if (role !== "test") { speak(role); timer = setInterval(() => speak(role), 8000); }
  }
  function mute(on) {
    muted = !!on;
    if (muted) { try { speechSynthesis.cancel(); } catch (e) {} if (ctx && master) master.gain.setTargetAtTime(0, ctx.currentTime, 0.03); }
    else level(LEVEL);
  }
  function beep() {
    const c = ensure(); if (!c || active) return;
    const o = c.createOscillator(), g = c.createGain();
    o.frequency.value = 880; g.gain.setValueAtTime(0.25, c.currentTime); g.gain.exponentialRampToValueAtTime(0.001, c.currentTime + 0.15);
    o.connect(g); g.connect(c.destination); o.start(); o.stop(c.currentTime + 0.16);
  }
  window.Alarm = { beep, unlock, start, stop, mute, get active() { return active; }, get running() { return !!ctx && ctx.state === "running"; } };
})();