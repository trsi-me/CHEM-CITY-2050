const chemAudio = (function () {
 const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
 let on = localStorage.getItem("chem_sound") !== "0";
 let ctx = null;

 function openCtx() {
  if (!window.AudioContext && !window.webkitAudioContext) {
   return null;
  }
  if (!ctx) {
   ctx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (ctx.state === "suspended") {
   ctx.resume();
  }
  return ctx;
 }

 function tone(freq, dur, type, vol) {
  if (!on || reduce) {
   return;
  }
  const ac = openCtx();
  if (!ac) {
   return;
  }
  const osc = ac.createOscillator();
  const gain = ac.createGain();
  osc.type = type;
  osc.frequency.value = freq;
  osc.connect(gain);
  gain.connect(ac.destination);
  const t = ac.currentTime;
  gain.gain.setValueAtTime(vol, t);
  gain.gain.exponentialRampToValueAtTime(0.001, t + dur);
  osc.start(t);
  osc.stop(t + dur);
 }

 function click() {
  tone(920, 0.07, "sine", 0.035);
 }

 function submit() {
  tone(420, 0.1, "triangle", 0.04);
  window.setTimeout(function () {
   tone(640, 0.14, "sine", 0.04);
  }, 70);
 }

 function sim() {
  tone(520, 0.12, "sine", 0.045);
  window.setTimeout(function () {
   tone(780, 0.18, "sine", 0.04);
  }, 90);
 }

 function setEnabled(value) {
  on = value;
  localStorage.setItem("chem_sound", on ? "1" : "0");
 }

 function enabled() {
  return on;
 }

 const api = { click: click, submit: submit, sim: sim, setEnabled: setEnabled, enabled: enabled, openCtx: openCtx };
 window.chemAudio = api;
 return api;
})();
