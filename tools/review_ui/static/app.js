const state = {
  song: null,
  inspection: null,
  timing: null,
  selectedIndex: 0,
  peaks: [],
  duration: 0,
  dragging: null,
};

const els = {
  songSelect: document.getElementById("songSelect"),
  songInput: document.getElementById("songInput"),
  loadSong: document.getElementById("loadSong"),
  songState: document.getElementById("songState"),
  lineList: document.getElementById("lineList"),
  audio: document.getElementById("audio"),
  playPause: document.getElementById("playPause"),
  clock: document.getElementById("clock"),
  waveform: document.getElementById("waveform"),
  zoomWaveform: document.getElementById("zoomWaveform"),
  focusText: document.getElementById("focusText"),
  focusTimes: document.getElementById("focusTimes"),
  prevLine: document.getElementById("prevLine"),
  nextLine: document.getElementById("nextLine"),
  setStart: document.getElementById("setStart"),
  setEnd: document.getElementById("setEnd"),
  saveTiming: document.getElementById("saveTiming"),
  renderProof: document.getElementById("renderProof"),
  saveStatus: document.getElementById("saveStatus"),
  jobLog: document.getElementById("jobLog"),
};

function fmt(ms) {
  if (!Number.isFinite(ms)) return "--:--.---";
  const sign = ms < 0 ? "-" : "";
  let value = Math.abs(Math.round(ms));
  const minutes = Math.floor(value / 60000);
  value -= minutes * 60000;
  const seconds = Math.floor(value / 1000);
  const millis = value - seconds * 1000;
  return `${sign}${minutes}:${String(seconds).padStart(2, "0")}.${String(millis).padStart(3, "0")}`;
}

function currentMs() {
  return Math.round(els.audio.currentTime * 1000);
}

function segments() {
  return state.timing?.segments || [];
}

function selectedSegment() {
  return segments()[state.selectedIndex] || null;
}

function setStatus(message) {
  els.saveStatus.textContent = message;
}

function setJobLog(message) {
  els.jobLog.textContent = message || "";
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }
  return data;
}

async function loadSongs() {
  const data = await fetchJson("/api/songs");
  els.songSelect.innerHTML = "";
  for (const song of data.songs) {
    const option = document.createElement("option");
    option.value = song;
    option.textContent = song;
    els.songSelect.appendChild(option);
  }
}

function querySong() {
  const params = new URLSearchParams(window.location.search);
  return params.get("song");
}

async function loadSong(songRef) {
  if (!songRef) return;
  setStatus("Loading song...");
  state.song = songRef;
  const inspection = await fetchJson(`/api/song?song=${encodeURIComponent(songRef)}`);
  state.inspection = inspection;
  renderSongState();

  if (!inspection.review_ui) {
    throw new Error("Song is not ready for review UI. Create song.json and timing first.");
  }

  const timingData = await fetchJson(inspection.review_ui.timing_url);
  state.timing = timingData.timing;
  state.selectedIndex = 0;
  els.audio.src = inspection.review_ui.audio_url;
  els.audio.load();
  await decodeWaveform(inspection.review_ui.audio_url);
  renderAll();
  setStatus("Loaded.");
}

function renderSongState() {
  const info = state.inspection;
  if (!info) {
    els.songState.textContent = "Load a song to inspect it.";
    return;
  }
  const cfg = info.config || {};
  const timing = info.timing || {};
  const lines = [
    `Song: ${info.song_dir_name}`,
    `Status: ${info.status}`,
    `Title: ${cfg.title || "(missing)"}`,
    `Audio: ${cfg.audio || "(missing)"}`,
    `Lyrics: ${cfg.lyrics || "(missing)"}`,
    `Timing: ${timing.present ? timing.path : "(missing)"}`,
    `Segments: ${timing.segment_count || 0}`,
    `Exports: ${(info.exports || []).length}`,
  ];
  if (info.validation?.errors?.length) {
    lines.push("", "Errors:", ...info.validation.errors.map((x) => `- ${x}`));
  }
  if (info.next_actions?.length) {
    lines.push("", "Next:", ...info.next_actions.map((x) => `- ${x.command || x.label}`));
  }
  els.songState.textContent = lines.join("\n");
}

function renderLineList() {
  els.lineList.innerHTML = "";
  segments().forEach((segment, index) => {
    const button = document.createElement("button");
    button.className = `line-row ${index === state.selectedIndex ? "active" : ""} ${segment.end_ms > segment.start_ms ? "valid" : ""}`;
    button.innerHTML = `
      <span class="dot"></span>
      <span class="line-time">${fmt(segment.start_ms)}</span>
      <span class="line-text"></span>
    `;
    button.querySelector(".line-text").textContent = segment.text || segment.id;
    button.addEventListener("click", () => {
      selectIndex(index, true);
    });
    els.lineList.appendChild(button);
  });
}

function renderFocus() {
  const segment = selectedSegment();
  if (!segment) {
    els.focusText.textContent = "No lyric selected";
    els.focusTimes.textContent = "";
    return;
  }
  els.focusText.textContent = segment.text;
  els.focusTimes.textContent = `${segment.id} | start ${fmt(segment.start_ms)} | end ${fmt(segment.end_ms)} | duration ${fmt(segment.end_ms - segment.start_ms)}`;
}

function renderAll() {
  renderLineList();
  renderFocus();
  drawWaveform();
  drawZoomWaveform();
}

function selectIndex(index, seek = false) {
  const count = segments().length;
  if (!count) return;
  state.selectedIndex = Math.max(0, Math.min(count - 1, index));
  const segment = selectedSegment();
  if (seek && segment) {
    els.audio.currentTime = Math.max(0, segment.start_ms / 1000);
  }
  renderAll();
}

async function decodeWaveform(audioUrl) {
  setStatus("Decoding waveform...");
  state.peaks = [];
  const response = await fetch(audioUrl);
  const arrayBuffer = await response.arrayBuffer();
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  const context = new AudioContextClass();
  const buffer = await context.decodeAudioData(arrayBuffer.slice(0));
  const channel = buffer.getChannelData(0);
  const bucketCount = 1000;
  const bucketSize = Math.max(1, Math.floor(channel.length / bucketCount));
  const peaks = [];
  for (let bucket = 0; bucket < bucketCount; bucket += 1) {
    let sum = 0;
    const start = bucket * bucketSize;
    const end = Math.min(channel.length, start + bucketSize);
    for (let index = start; index < end; index += 1) {
      sum += Math.abs(channel[index]);
    }
    peaks.push(Math.min(1, sum / Math.max(1, end - start) * 4));
  }
  state.duration = buffer.duration;
  state.peaks = peaks;
  await context.close();
}

function canvasTime(event) {
  const rect = els.waveform.getBoundingClientRect();
  const x = Math.max(0, Math.min(rect.width, event.clientX - rect.left));
  return (x / rect.width) * Math.max(state.duration, els.audio.duration || 0);
}

function timeToX(seconds, width) {
  const duration = Math.max(state.duration, els.audio.duration || 0, 1);
  return (seconds / duration) * width;
}

function selectedZoomWindow() {
  const selected = selectedSegment();
  const duration = Math.max(state.duration, els.audio.duration || 0, 1);
  if (!selected) return { start: 0, end: Math.min(duration, 10) };
  const start = selected.start_ms / 1000;
  const end = selected.end_ms / 1000;
  const center = (start + end) / 2;
  const span = Math.max(4, end - start + 1.5);
  const windowStart = Math.max(0, center - span / 2);
  const windowEnd = Math.min(duration, windowStart + span);
  return {
    start: Math.max(0, windowEnd - span),
    end: windowEnd,
  };
}

function timeToZoomX(seconds, width) {
  const win = selectedZoomWindow();
  return ((seconds - win.start) / Math.max(0.001, win.end - win.start)) * width;
}

function zoomXToTime(event) {
  const rect = els.zoomWaveform.getBoundingClientRect();
  const x = Math.max(0, Math.min(rect.width, event.clientX - rect.left));
  const win = selectedZoomWindow();
  return win.start + (x / rect.width) * (win.end - win.start);
}

function drawPeaks(ctx, width, height, startSeconds, endSeconds) {
  const mid = height / 2;
  const peaks = state.peaks.length ? state.peaks : new Array(160).fill(0.05);
  const duration = Math.max(state.duration, els.audio.duration || 0, 1);
  const startBucket = Math.max(0, Math.floor((startSeconds / duration) * peaks.length));
  const endBucket = Math.min(peaks.length - 1, Math.ceil((endSeconds / duration) * peaks.length));
  const visible = peaks.slice(startBucket, Math.max(startBucket + 1, endBucket + 1));
  const barWidth = width / visible.length;
  visible.forEach((peak, index) => {
    const x = index * barWidth;
    const h = Math.max(2, peak * height * 0.82);
    ctx.fillStyle = index % 2 ? "#35402e" : "#425038";
    ctx.fillRect(x, mid - h / 2, Math.max(1, barWidth * 0.72), h);
  });
}

function drawWaveform() {
  const canvas = els.waveform;
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * scale));
  canvas.height = Math.max(1, Math.floor(rect.height * scale));
  ctx.scale(scale, scale);

  const width = rect.width;
  const height = rect.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#0d110c";
  ctx.fillRect(0, 0, width, height);

  drawPeaks(ctx, width, height, 0, Math.max(state.duration, els.audio.duration || 0, 1));

  const playX = timeToX(els.audio.currentTime || 0, width);
  ctx.strokeStyle = "#f1b84b";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(playX, 0);
  ctx.lineTo(playX, height);
  ctx.stroke();

  for (const segment of segments()) {
    const startX = timeToX(segment.start_ms / 1000, width);
    const endX = timeToX(segment.end_ms / 1000, width);
    ctx.fillStyle = "rgba(128, 199, 122, 0.08)";
    ctx.fillRect(startX, 0, Math.max(1, endX - startX), height);
  }

  const selected = selectedSegment();
  if (selected) {
    const startX = timeToX(selected.start_ms / 1000, width);
    const endX = timeToX(selected.end_ms / 1000, width);
    ctx.fillStyle = "rgba(241, 184, 75, 0.22)";
    ctx.fillRect(startX, 0, Math.max(2, endX - startX), height);
    ctx.strokeStyle = "#f1b84b";
    ctx.lineWidth = 3;
    for (const x of [startX, endX]) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
      ctx.fillStyle = "#f1b84b";
      ctx.fillRect(x - 5, 0, 10, height);
    }
  }
}

function drawZoomWaveform() {
  const canvas = els.zoomWaveform;
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * scale));
  canvas.height = Math.max(1, Math.floor(rect.height * scale));
  ctx.scale(scale, scale);

  const width = rect.width;
  const height = rect.height;
  const win = selectedZoomWindow();
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#0d110c";
  ctx.fillRect(0, 0, width, height);
  drawPeaks(ctx, width, height, win.start, win.end);

  const playX = timeToZoomX(els.audio.currentTime || 0, width);
  if (playX >= 0 && playX <= width) {
    ctx.strokeStyle = "#f1b84b";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(playX, 0);
    ctx.lineTo(playX, height);
    ctx.stroke();
  }

  const selected = selectedSegment();
  if (selected) {
    const startX = timeToZoomX(selected.start_ms / 1000, width);
    const endX = timeToZoomX(selected.end_ms / 1000, width);
    ctx.fillStyle = "rgba(241, 184, 75, 0.25)";
    ctx.fillRect(startX, 0, Math.max(2, endX - startX), height);
    ctx.strokeStyle = "#f1b84b";
    ctx.lineWidth = 4;
    for (const x of [startX, endX]) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
      ctx.fillStyle = "#f1b84b";
      ctx.fillRect(x - 7, 0, 14, height);
    }
  }

  ctx.fillStyle = "#a8ad98";
  ctx.font = "12px Cascadia Mono, monospace";
  ctx.fillText(`${fmt(win.start * 1000)} - ${fmt(win.end * 1000)}`, 10, height - 10);
}

function nearestHandle(event, zoom = false) {
  const selected = selectedSegment();
  if (!selected) return null;
  const rect = (zoom ? els.zoomWaveform : els.waveform).getBoundingClientRect();
  const x = event.clientX - rect.left;
  const startX = zoom ? timeToZoomX(selected.start_ms / 1000, rect.width) : timeToX(selected.start_ms / 1000, rect.width);
  const endX = zoom ? timeToZoomX(selected.end_ms / 1000, rect.width) : timeToX(selected.end_ms / 1000, rect.width);
  const hitSize = zoom ? 28 : 18;
  if (Math.abs(x - startX) < hitSize) return "start";
  if (Math.abs(x - endX) < hitSize) return "end";
  return null;
}

function setSegmentTime(kind, ms) {
  const selected = selectedSegment();
  if (!selected) return;
  if (kind === "start") {
    selected.start_ms = Math.max(0, Math.min(ms, selected.end_ms - 50));
  } else {
    selected.end_ms = Math.max(selected.start_ms + 50, ms);
  }
  renderAll();
}

function nudgeSelected(deltaMs) {
  const selected = selectedSegment();
  if (!selected) return;
  selected.start_ms = Math.max(0, selected.start_ms + deltaMs);
  selected.end_ms = Math.max(selected.start_ms + 50, selected.end_ms + deltaMs);
  renderAll();
}

function nudgeBoundary(kind, deltaMs) {
  const selected = selectedSegment();
  if (!selected) return;
  if (kind === "start") {
    setSegmentTime("start", selected.start_ms + deltaMs);
  } else {
    setSegmentTime("end", selected.end_ms + deltaMs);
  }
}

els.waveform.addEventListener("mousedown", (event) => {
  const handle = nearestHandle(event);
  if (handle) {
    state.dragging = handle;
    return;
  }
  els.audio.currentTime = canvasTime(event);
  drawWaveform();
});

els.zoomWaveform.addEventListener("mousedown", (event) => {
  const handle = nearestHandle(event, true);
  if (handle) {
    state.dragging = `zoom:${handle}`;
    return;
  }
  els.audio.currentTime = zoomXToTime(event);
  drawWaveform();
  drawZoomWaveform();
});

window.addEventListener("mousemove", (event) => {
  if (!state.dragging) return;
  if (state.dragging.startsWith("zoom:")) {
    setSegmentTime(state.dragging.split(":")[1], Math.round(zoomXToTime(event) * 1000));
  } else {
    setSegmentTime(state.dragging, Math.round(canvasTime(event) * 1000));
  }
});

window.addEventListener("mouseup", () => {
  state.dragging = null;
});

els.audio.addEventListener("timeupdate", () => {
  els.clock.textContent = fmt(currentMs());
  const index = segments().findIndex((segment) => currentMs() >= segment.start_ms && currentMs() <= segment.end_ms);
  if (index >= 0 && index !== state.selectedIndex && !state.dragging) {
    state.selectedIndex = index;
    renderLineList();
    renderFocus();
  }
  drawWaveform();
  drawZoomWaveform();
});

els.audio.addEventListener("play", () => {
  els.playPause.textContent = "Pause";
});

els.audio.addEventListener("pause", () => {
  els.playPause.textContent = "Play";
});

els.playPause.addEventListener("click", () => {
  if (els.audio.paused) {
    els.audio.play();
  } else {
    els.audio.pause();
  }
});

els.prevLine.addEventListener("click", () => selectIndex(state.selectedIndex - 1, true));
els.nextLine.addEventListener("click", () => selectIndex(state.selectedIndex + 1, true));
els.setStart.addEventListener("click", () => setSegmentTime("start", currentMs()));
els.setEnd.addEventListener("click", () => setSegmentTime("end", currentMs()));

document.querySelectorAll("[data-nudge-line]").forEach((button) => {
  button.addEventListener("click", () => nudgeSelected(Number(button.dataset.nudgeLine)));
});

document.querySelectorAll("[data-nudge-start]").forEach((button) => {
  button.addEventListener("click", () => nudgeBoundary("start", Number(button.dataset.nudgeStart)));
});

document.querySelectorAll("[data-nudge-end]").forEach((button) => {
  button.addEventListener("click", () => nudgeBoundary("end", Number(button.dataset.nudgeEnd)));
});

els.saveTiming.addEventListener("click", async () => {
  if (!state.song || !state.timing) return;
  try {
    setStatus("Saving...");
    const data = await fetchJson(`/api/song/timing?song=${encodeURIComponent(state.song)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timing: state.timing }),
    });
    setStatus(`Saved. Backup: ${data.backup || "none"}`);
  } catch (error) {
    setStatus(`Save failed: ${error.message}`);
  }
});

els.renderProof.addEventListener("click", async () => {
  if (!state.song) return;
  try {
    setStatus("Rendering proof...");
    setJobLog("");
    const data = await fetchJson("/api/song/render-proof", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ song: state.song, target: "horizontal", layout: "soft_scroll" }),
    });
    setStatus(data.ok ? "Proof render complete." : "Proof render failed.");
    setJobLog(`${data.command.join(" ")}\n\nSTDOUT:\n${data.stdout}\n\nSTDERR:\n${data.stderr}`);
  } catch (error) {
    setStatus(`Render failed: ${error.message}`);
    setJobLog(error.stack || String(error));
  }
});

els.loadSong.addEventListener("click", () => {
  const typed = els.songInput.value.trim();
  const selected = els.songSelect.value;
  loadSong(typed || selected).catch((error) => setStatus(`Load failed: ${error.message}`));
});

window.addEventListener("keydown", (event) => {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement) return;
  if (event.code === "Space") {
    event.preventDefault();
    els.playPause.click();
  }
  if (event.code === "ArrowUp") {
    event.preventDefault();
    selectIndex(state.selectedIndex - 1, true);
  }
  if (event.code === "ArrowDown") {
    event.preventDefault();
    selectIndex(state.selectedIndex + 1, true);
  }
  if (event.code === "BracketLeft") {
    event.preventDefault();
    setSegmentTime("start", currentMs());
  }
  if (event.code === "BracketRight") {
    event.preventDefault();
    setSegmentTime("end", currentMs());
  }
});

window.addEventListener("resize", drawWaveform);
window.addEventListener("resize", drawZoomWaveform);

loadSongs()
  .then(() => {
    const initial = querySong();
    if (initial) {
      els.songInput.value = initial;
      return loadSong(initial);
    }
    if (els.songSelect.value) {
      return loadSong(els.songSelect.value);
    }
    return null;
  })
  .catch((error) => setStatus(`Startup failed: ${error.message}`));
