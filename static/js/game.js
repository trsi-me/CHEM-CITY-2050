const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function paintMeters() {
 const nodes = document.querySelectorAll("[data-meter]");
 for (let i = 0; i < nodes.length; i += 1) {
  const node = nodes[i];
  const bar = node.querySelector(".bar");
  if (!bar) continue;
  const max = Number(node.getAttribute("data-max") || "100");
  const from = Number(node.getAttribute("data-from"));
  const to = Number(node.getAttribute("data-to"));
  const start = reduce ? to : from;
  bar.style.width = ((start * 100) / max) + "%";
  if (!reduce) requestAnimationFrame(() => { bar.style.width = ((to * 100) / max) + "%"; });
 }
 const rings = document.querySelectorAll("[data-ring]");
 for (let j = 0; j < rings.length; j += 1) {
  const ring = rings[j];
  const from = Number(ring.getAttribute("data-from"));
  const to = Number(ring.getAttribute("data-to"));
  const start = reduce ? to : from;
  ring.style.setProperty("--p", start + "%");
  if (!reduce) requestAnimationFrame(() => { ring.style.setProperty("--p", to + "%"); });
 }
}

function bindForm() {
 const form = document.querySelector(".decision-form");
 if (!form) return;
 function lock() {
  const button = form.querySelector(".submit");
  button.disabled = true;
  button.textContent = "جارٍ حساب الأثر";
  if (window.chemAudio) chemAudio.submit();
 }
 form.addEventListener("submit", lock);
}

function bindPrint() {
 const button = document.querySelector(".print");
 if (!button) return;
 button.addEventListener("click", () => window.print());
}

function bindPassToggle() {
 const buttons = document.querySelectorAll("[data-pass-toggle]");
 for (let i = 0; i < buttons.length; i += 1) {
  const button = buttons[i];
  button.addEventListener("click", () => {
   const wrap = button.closest(".pass-wrap");
   if (!wrap) return;
   const field = wrap.querySelector("input");
   if (!field) return;
   const show = field.type === "password";
   field.type = show ? "text" : "password";
   button.textContent = show ? "إخفاء" : "إظهار";
  });
 }
}

function bindSoundUi() {
 const toggle = document.getElementById("soundToggle");
 if (!toggle || !window.chemAudio) return;
 function sync() {
  const on = chemAudio.enabled();
  toggle.setAttribute("aria-pressed", on ? "true" : "false");
  toggle.textContent = on ? "الصوت: تشغيل" : "الصوت: كتم";
 }
 sync();
 toggle.addEventListener("click", () => {
  chemAudio.setEnabled(!chemAudio.enabled());
  chemAudio.openCtx();
  if (chemAudio.enabled()) chemAudio.click();
  sync();
 });
 document.body.addEventListener("click", (event) => {
  const target = event.target.closest(".btn, .choice, .option, .link-btn, .pass-toggle, .sound-btn");
  if (!target || target.id === "soundToggle") return;
  chemAudio.openCtx();
  chemAudio.click();
 });
}

function focusSim() {
 const sim = document.getElementById("sim");
 if (!sim) return;
 if (window.chemAudio) chemAudio.sim();
 sim.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
}

paintMeters();
bindForm();
bindPrint();
bindPassToggle();
bindSoundUi();
focusSim();
