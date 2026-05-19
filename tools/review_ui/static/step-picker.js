// Song picker wiring for the new step pages. NOT loaded on index.html
// (the timing editor has its own picker wiring inside app.js that
// loads timing data without leaving the page). Here on step pages we
// just navigate to the same step with a new ?song= param so each step
// page can fetch its own state.

(async function populateSongPicker() {
  const select = document.getElementById("songSelect");
  if (!select) return;
  try {
    const res = await fetch("/api/songs");
    const data = await res.json();
    select.innerHTML = "";
    for (const name of (data.songs || [])) {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      select.appendChild(opt);
    }
    const current = currentSongRef();
    if (current) select.value = current;
  } catch (_err) {
    // Server unreachable; leave select empty rather than throwing.
  }
})();

(function wireSongPickerNav() {
  const button = document.getElementById("loadSong");
  const select = document.getElementById("songSelect");
  const input = document.getElementById("songInput");
  if (input && currentSongRef()) input.value = currentSongRef();
  if (select) {
    select.addEventListener("change", () => {
      if (input) input.value = select.value;
    });
  }
  if (button) {
    button.addEventListener("click", () => {
      const typed = (input && input.value.trim()) || (select && select.value) || "";
      if (!typed) return;
      const active = LYRIC_STEPS.find((s) => s.slug === currentLyricStep()) || LYRIC_STEPS[2];
      const url = new URL(active.href, window.location.origin);
      url.searchParams.set("song", typed);
      window.location.href = url.toString();
    });
  }
})();
