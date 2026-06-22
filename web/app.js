/* Ambient AI — voice-mode web client.
 *
 * Listens continuously via the Web Speech API, keeps a rolling transcript,
 * and after each utterance asks Gemini whether to stay SILENT or INTERVENE.
 * It speaks aloud only when the model decides it can genuinely help.
 * The default state is always silence.
 */

"use strict";

// ---------- Configuration & persisted settings ----------

const STORE_KEY = "ambient-ai-settings";

const DEFAULTS = {
  apiKey: "",
  model: "gemini-2.5-flash",
  cooldown: 15,
  sensitivity: 1, // 0 = reluctant, 1 = balanced, 2 = eager
  voiceURI: "",
  speakReplies: true,
};

const SENSITIVITY_LABELS = ["Reserved", "Balanced", "Eager"];

// Extra guidance appended to the prompt based on the eagerness slider.
const SENSITIVITY_GUIDANCE = {
  0: "Be extremely conservative. Only speak if there is an explicit, unanswered factual question AND you are completely certain. When unsure, stay SILENT.",
  1: "Use balanced judgement as described above.",
  2: "You may be slightly more willing to help: if there is a clear factual gap or a likely-wrong fact and you are confident, offer a brief correction or answer.",
};

const BUFFER_MAX_UTTERANCES = 50;

function loadSettings() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (!raw) return { ...DEFAULTS };
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULTS };
  }
}

function saveSettings(settings) {
  localStorage.setItem(STORE_KEY, JSON.stringify(settings));
}

let settings = loadSettings();

// ---------- The intervention prompt (ported from the Python trigger) ----------

function buildPrompt(formattedTranscript, latestUtterance) {
  return `You are an ambient AI assistant silently listening to a conversation between people.
Your role is like a knowledgeable friend in the room — you almost never speak,
but when you do, it is because you can genuinely help with a specific factual need.

Here is the conversation so far:
---
${formattedTranscript}
---

The most recent thing said was:
"${latestUtterance}"

Decide if you should speak right now. Respond with EXACTLY one of:
1. The word SILENT (if you should not speak)
2. INTERVENE: followed by your response (if you should speak)

You should ONLY intervene when ALL of these are true:
- Someone asked a question that went unanswered OR expressed uncertainty about a fact
- You have reliable knowledge that directly answers their question
- Your response would be brief (under 30 words)
- The moment is right — they are not mid-sentence or mid-thought

You should NEVER intervene for:
- Opinions or personal preferences
- Emotional topics or sensitive conversations
- Rhetorical questions
- Things already resolved in the conversation
- Small talk or filler phrases
- Any topic where you are not certain of the answer

${SENSITIVITY_GUIDANCE[settings.sensitivity] || SENSITIVITY_GUIDANCE[1]}

Your response if intervening must be natural, spoken aloud, extremely brief,
like a person casually answering. Do not say "As an AI" or introduce yourself.
Just give the answer naturally, the way a knowledgeable friend would say it mid-conversation.

Respond now with SILENT or INTERVENE: [your response]`;
}

// ---------- Conversation buffer ----------

const buffer = [];

function bufferAdd(speaker, text) {
  buffer.push({ speaker, text, ts: Date.now() });
  while (buffer.length > BUFFER_MAX_UTTERANCES) buffer.shift();
}

function formattedTranscript() {
  return buffer.map((u) => `[${u.speaker}]: ${u.text}`).join("\n");
}

// ---------- Gemini call ----------

async function callGemini(prompt) {
  const url =
    `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(settings.model)}:generateContent?key=${encodeURIComponent(settings.apiKey)}`;
  const body = {
    contents: [{ role: "user", parts: [{ text: prompt }] }],
    generationConfig: { temperature: 0.4, maxOutputTokens: 80 },
  };
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = "";
    try {
      const err = await res.json();
      detail = err?.error?.message || "";
    } catch { /* ignore */ }
    throw new Error(`Gemini ${res.status}: ${detail || res.statusText}`);
  }
  const data = await res.json();
  const parts = data?.candidates?.[0]?.content?.parts;
  const text = Array.isArray(parts) ? parts.map((p) => p.text || "").join("") : "";
  return (text || "").trim();
}

// ---------- Intervention trigger (default-silent, cooldown) ----------

let lastSpokeAt = 0;

async function evaluate(latestUtterance) {
  const sinceLast = (Date.now() - lastSpokeAt) / 1000;
  if (sinceLast < settings.cooldown) {
    log(`SILENT (cooldown ${sinceLast.toFixed(1)}/${settings.cooldown}s)`);
    return null;
  }
  let raw;
  try {
    raw = await callGemini(buildPrompt(formattedTranscript(), latestUtterance));
  } catch (e) {
    log(`Gemini error -> SILENT: ${e.message}`);
    showToast(`Gemini error: ${e.message}`, "error");
    return null;
  }
  if (/^INTERVENE:/i.test(raw)) {
    const reply = raw.slice(raw.indexOf(":") + 1).trim();
    if (!reply) {
      log("INTERVENE with empty body -> SILENT");
      return null;
    }
    lastSpokeAt = Date.now();
    log(`INTERVENE -> ${reply}`);
    return reply;
  }
  if (/^SILENT$/i.test(raw)) {
    log("SILENT (model chose silence)");
    return null;
  }
  log(`Unexpected response -> SILENT: ${raw}`);
  return null;
}

// ---------- Speech recognition ----------

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

let recognition = null;
let listening = false;       // user intent to listen
let recognizing = false;     // recognition actually running
let suspendForSpeech = false; // paused while TTS speaks

function createRecognition() {
  const rec = new SpeechRecognition();
  rec.continuous = true;
  rec.interimResults = true;
  rec.lang = "en-US";

  rec.onstart = () => { recognizing = true; };

  rec.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      const text = result[0].transcript.trim();
      if (result.isFinal) {
        if (text) handleFinalUtterance(text);
      } else {
        interim += text + " ";
      }
    }
    els.interim.textContent = interim.trim();
  };

  rec.onerror = (event) => {
    if (event.error === "not-allowed" || event.error === "service-not-allowed") {
      showToast("Microphone permission denied.", "error");
      stopListening();
    } else if (event.error === "no-speech" || event.error === "aborted") {
      // benign — onend will auto-restart
    } else {
      log(`Recognition error: ${event.error}`);
    }
  };

  rec.onend = () => {
    recognizing = false;
    els.interim.textContent = "";
    // Auto-restart unless the user stopped or we are speaking.
    if (listening && !suspendForSpeech) {
      try { rec.start(); } catch { /* already starting */ }
    }
  };

  return rec;
}

let processing = false;

async function handleFinalUtterance(text) {
  // Ignore the assistant accidentally hearing itself / duplicates.
  if (processing) {
    bufferAdd("Speaker", text);
    addBubble("user", text);
    return;
  }
  processing = true;
  bufferAdd("Speaker", text);
  addBubble("user", text);

  setState("thinking");
  const reply = await evaluate(text);
  processing = false;

  if (reply) {
    addBubble("ai", reply);
    bufferAdd("Assistant", reply);
    await speak(reply);
  }
  setState(listening ? "listening" : "idle");
}

function startListening() {
  if (!SpeechRecognition) {
    showToast("This browser doesn't support speech recognition. Try Chrome.", "error");
    return;
  }
  if (!settings.apiKey) {
    showToast("Add your Gemini API key in settings first.", "error");
    openSettings();
    return;
  }
  listening = true;
  recognition = recognition || createRecognition();
  try { recognition.start(); } catch { /* already running */ }
  startVisualizer();
  setState("listening");
  els.micBtn.setAttribute("aria-pressed", "true");
  els.micBtn.querySelector(".mic-btn-label").textContent = "Stop listening";
}

function stopListening() {
  listening = false;
  if (recognition) { try { recognition.stop(); } catch { /* noop */ } }
  stopVisualizer();
  setState("idle");
  els.micBtn.setAttribute("aria-pressed", "false");
  els.micBtn.querySelector(".mic-btn-label").textContent = "Start listening";
  els.interim.textContent = "";
}

// ---------- Text to speech ----------

let voices = [];

function refreshVoices() {
  voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
  const sel = els.voice;
  const current = settings.voiceURI;
  sel.innerHTML = '<option value="">System default</option>';
  voices.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v.voiceURI;
    opt.textContent = `${v.name} (${v.lang})`;
    if (v.voiceURI === current) opt.selected = true;
    sel.appendChild(opt);
  });
}

function speak(text) {
  return new Promise((resolve) => {
    if (!settings.speakReplies || !window.speechSynthesis) { resolve(); return; }
    // Pause recognition so we don't transcribe our own voice.
    suspendForSpeech = true;
    if (recognition && recognizing) { try { recognition.stop(); } catch { /* noop */ } }

    setState("speaking");
    const utter = new SpeechSynthesisUtterance(text);
    utter.rate = 1.02;
    utter.pitch = 1.0;
    utter.volume = 1.0;
    const v = voices.find((x) => x.voiceURI === settings.voiceURI);
    if (v) utter.voice = v;

    const finish = () => {
      suspendForSpeech = false;
      // Resume listening if still active.
      if (listening && recognition && !recognizing) {
        try { recognition.start(); } catch { /* noop */ }
      }
      resolve();
    };
    utter.onend = finish;
    utter.onerror = finish;
    window.speechSynthesis.speak(utter);
  });
}

// ---------- Mic-volume visualizer ----------

let audioCtx = null, analyser = null, micStream = null, rafId = null;

async function startVisualizer() {
  try {
    if (!micStream) {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    }
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") await audioCtx.resume();
    const source = audioCtx.createMediaStreamSource(micStream);
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);

    const tick = () => {
      analyser.getByteFrequencyData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i++) sum += data[i];
      const level = Math.min(1, (sum / data.length) / 90);
      els.orbWrap.style.setProperty("--pulse", level.toFixed(3));
      rafId = requestAnimationFrame(tick);
    };
    tick();
  } catch (e) {
    log(`Visualizer unavailable: ${e.message}`);
  }
}

function stopVisualizer() {
  if (rafId) cancelAnimationFrame(rafId);
  rafId = null;
  els.orbWrap.style.setProperty("--pulse", "0");
}

// ---------- UI helpers ----------

const els = {};
function cache() {
  [
    "orbWrap", "statusLine", "interim", "micBtn", "hint",
    "transcript", "transcriptToggle", "transcriptList", "transcriptEmpty",
    "settingsModal", "settingsBtn", "closeSettings", "saveSettings", "clearBtn",
    "apiKey", "model", "cooldown", "cooldownVal", "sensitivity", "sensitivityVal",
    "voice", "speakReplies", "toast",
  ].forEach((id) => { els[id] = document.getElementById(id); });
}

const STATE_TEXT = {
  idle: "Idle — press start to begin listening",
  listening: "Listening…",
  thinking: "Thinking…",
  speaking: "Speaking…",
};

function setState(state) {
  els.orbWrap.dataset.state = state;
  els.statusLine.textContent = STATE_TEXT[state] || "";
}

function addBubble(who, text) {
  els.transcriptEmpty.style.display = "none";
  const b = document.createElement("div");
  b.className = `bubble ${who}`;
  const label = document.createElement("span");
  label.className = "who";
  label.textContent = who === "ai" ? "Ambient AI" : "Speaker";
  const body = document.createElement("span");
  body.textContent = text;
  b.appendChild(label);
  b.appendChild(body);
  els.transcriptList.appendChild(b);
  els.transcript.scrollTop = els.transcript.scrollHeight;
}

let toastTimer = null;
function showToast(msg, kind = "") {
  els.toast.textContent = msg;
  els.toast.className = `toast ${kind}`;
  els.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { els.toast.hidden = true; }, 4200);
}

function log(msg) {
  console.log(`[ambient] ${msg}`);
}

// ---------- Settings modal ----------

function openSettings() {
  els.apiKey.value = settings.apiKey;
  els.model.value = settings.model;
  els.cooldown.value = settings.cooldown;
  els.cooldownVal.textContent = `${settings.cooldown}s`;
  els.sensitivity.value = settings.sensitivity;
  els.sensitivityVal.textContent = SENSITIVITY_LABELS[settings.sensitivity];
  els.speakReplies.checked = settings.speakReplies;
  refreshVoices();
  els.settingsModal.hidden = false;
}

function closeSettings() { els.settingsModal.hidden = true; }

function persistFromModal() {
  settings = {
    ...settings,
    apiKey: els.apiKey.value.trim(),
    model: els.model.value,
    cooldown: parseInt(els.cooldown.value, 10),
    sensitivity: parseInt(els.sensitivity.value, 10),
    voiceURI: els.voice.value,
    speakReplies: els.speakReplies.checked,
  };
  saveSettings(settings);
  closeSettings();
  showToast("Settings saved.", "success");
}

// ---------- Wire up ----------

function init() {
  cache();
  setState("idle");

  els.micBtn.addEventListener("click", () => {
    if (listening) stopListening(); else startListening();
  });

  els.settingsBtn.addEventListener("click", openSettings);
  els.closeSettings.addEventListener("click", closeSettings);
  els.saveSettings.addEventListener("click", persistFromModal);
  els.settingsModal.addEventListener("click", (e) => {
    if (e.target === els.settingsModal) closeSettings();
  });

  els.cooldown.addEventListener("input", () => {
    els.cooldownVal.textContent = `${els.cooldown.value}s`;
  });
  els.sensitivity.addEventListener("input", () => {
    els.sensitivityVal.textContent = SENSITIVITY_LABELS[els.sensitivity.value];
  });

  els.transcriptToggle.addEventListener("click", () => {
    const open = els.transcript.classList.toggle("open");
    els.transcriptToggle.setAttribute("aria-expanded", String(open));
  });

  els.clearBtn.addEventListener("click", () => {
    buffer.length = 0;
    els.transcriptList.innerHTML = "";
    els.transcriptEmpty.style.display = "";
    lastSpokeAt = 0;
    showToast("Conversation cleared.");
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeSettings();
    if (e.code === "Space" && e.target === document.body) {
      e.preventDefault();
      if (listening) stopListening(); else startListening();
    }
  });

  if (window.speechSynthesis) {
    refreshVoices();
    window.speechSynthesis.onvoiceschanged = refreshVoices;
  }

  if (!SpeechRecognition) {
    els.hint.textContent = "Speech recognition needs a Chromium-based browser (Chrome, Edge).";
  }
  if (!settings.apiKey) {
    setTimeout(openSettings, 400);
  }
}

document.addEventListener("DOMContentLoaded", init);
