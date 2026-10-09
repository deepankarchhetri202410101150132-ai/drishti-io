// Phone-side mic: measures loudness and posts it to the laptop as the voice score.
let micCtx = null;
window.startMic = async function () {
  if (micCtx) return;
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  micCtx = new AudioContext();
  const an = micCtx.createAnalyser(); an.fftSize = 2048;
  micCtx.createMediaStreamSource(stream).connect(an);
  const buf = new Float32Array(an.fftSize);
  setInterval(() => {
    an.getFloatTimeDomainData(buf);
    const rms = Math.sqrt(buf.reduce((s, v) => s + v * v, 0) / buf.length);
    const voice = Math.min(100, rms * 400);
    fetch("/sensor-data", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ voice, cid: typeof CID !== "undefined" ? CID : null }) }).catch(() => {});
  }, 1000);
};