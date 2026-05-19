// Shared stepper renderer. Safe to include on any page that has a
// <nav class="stepper"></nav> element. Renders the canonical step list
// as anchors, marks the current step active by URL path, and propagates
// the current ?song= query parameter to every step link so the user
// stays scoped to the same song across the workflow.

const LYRIC_STEPS = [
  { slug: "intake",       label: "Intake",          href: "/step-intake.html" },
  { slug: "whisper",      label: "Whisper",         href: "/step-whisper.html" },
  { slug: "timing",       label: "Timing",          href: "/" },
  { slug: "style-prompt", label: "Style Prompt",    href: "/step-style-prompt.html" },
  { slug: "comfyui",      label: "ComfyUI",         href: "/step-comfyui.html" },
  { slug: "flux",         label: "Flux Candidates", href: "/step-flux.html" },
  { slug: "wan",          label: "Wan Candidates",  href: "/step-wan.html" },
];

function currentLyricStep() {
  const path = window.location.pathname;
  if (path === "/" || path.endsWith("/index.html")) return "timing";
  const match = path.match(/\/step-(.+?)\.html$/);
  return match ? match[1] : null;
}

function currentSongRef() {
  return new URLSearchParams(window.location.search).get("song") || "";
}

(function renderStepper() {
  const nav = document.querySelector("nav.stepper");
  if (!nav) return;
  const active = currentLyricStep();
  const song = currentSongRef();
  nav.innerHTML = "";
  for (const step of LYRIC_STEPS) {
    const link = document.createElement("a");
    link.className = "step" + (step.slug === active ? " active" : "");
    const url = new URL(step.href, window.location.origin);
    if (song) url.searchParams.set("song", song);
    link.href = url.toString();
    link.textContent = step.label;
    nav.appendChild(link);
  }
})();
