# Ambient Conversational AI Assistant

An ambient voice assistant that runs silently in a room, continuously listens to
everyone speaking, and only speaks up when it can genuinely add value — like a
knowledgeable friend who stays quiet almost all the time. There is no wake word:
it listens always and speaks almost never, intervening only when there is a clear,
answerable factual gap in the conversation.

It ships in two forms:

- **Web app (voice mode)** — a polished, ChatGPT/Claude-style voice UI that runs
  entirely in the browser and deploys to GitHub Pages. No install required. See
  [Web app (voice mode)](#web-app-voice-mode).
- **Python pipeline** — the original headless/server implementation using
  Whisper, pyannote, and pyttsx3. See [Python pipeline](#python-pipeline).

## Get a free Gemini API key

Both versions need a Google Gemini API key. The free tier is plenty:

1. Go to <https://aistudio.google.com/app/apikey>
2. Sign in with any Google account.
3. Click **Create API key** → **Create API key in new project**.
4. Copy the key (starts with `AIza...`).

The free tier covers `gemini-2.0-flash` and `gemini-1.5-flash` with generous
rate limits.

## Web app (voice mode)

The `web/` folder is a self-contained static app (HTML/CSS/JS, no build step).
It uses the browser's Web Speech API for continuous listening and speaking, and
calls Gemini directly from the browser. Your API key is stored only in your
browser's `localStorage` — it is never committed or sent anywhere except Google.

### Run it locally

```bash
# Any static server works; the app is plain HTML/CSS/JS.
cd web
python -m http.server 8000
# then open http://localhost:8000
```

Open settings (gear icon), paste your Gemini API key, then press **Start
listening** and talk naturally. The orb reacts to your voice; the assistant
stays silent until it can genuinely help, then replies in a chat bubble and
aloud.

> Speech recognition requires a Chromium-based browser (Chrome or Edge).

### Deploy to GitHub Pages (automatic)

A GitHub Actions workflow (`.github/workflows/deploy.yml`) publishes `web/` to
GitHub Pages on every push to `main`. To enable it once:

1. In the repo, go to **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions**.

After the next push to `main` (or a manual run from the Actions tab), the app is
live at `https://<owner>.github.io/Ambient-AI/`.

## Python pipeline

### How it works

Audio is captured from the microphone in 3-second chunks, transcribed with
OpenAI Whisper, optionally labeled by speaker (pyannote.audio), and appended to a
rolling conversation buffer. After every utterance, Google Gemini reads the full
context and decides whether to stay `SILENT` or `INTERVENE:` with a short spoken
reply, which is played aloud via pyttsx3. The default state is always silence.

```
microphone -> AudioCapture -> Transcriber -> Diarizer -> ConversationBuffer
                                                              |
                                                       InterventionTrigger (Gemini)
                                                              |
                                                   Responder -> speakers (pyttsx3)
```

## Prerequisites

- Python 3.11
- A working microphone (input)
- Working speakers (output)
- A Google Gemini API key
- (Optional) A HuggingFace token, only if you enable speaker diarization

On Linux you may also need PortAudio and an eSpeak backend for the audio
libraries:

```bash
sudo apt-get install -y portaudio19-dev libespeak1 espeak-ng ffmpeg
```

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/cliperguru-sudo/Ambient-AI.git
cd Ambient-AI

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your .env from the template and fill in your keys
cp .env.example .env
#   then edit .env and set GEMINI_API_KEY=...
```

## Running

```bash
python main.py
```

The assistant starts listening immediately. Spoken words appear as transcriptions
in the console and in `ambient_ai.log`. Press `Ctrl+C` to stop.

## Running the trigger tests

The trigger tests call the real Gemini API, so `GEMINI_API_KEY` must be set in
your `.env` first.

```bash
python -m tests.test_trigger
```

You should see at least 4 of the 5 sample conversations classified correctly.

## Enabling speaker diarization

By default diarization is off and every utterance is labeled `Speaker_Unknown`.
To distinguish between speakers:

1. Create a HuggingFace account and accept the model terms for
   `pyannote/speaker-diarization-3.1`.
2. Add your token to `.env`: `HUGGINGFACE_TOKEN=hf_...`
3. Set `DIARIZATION_ENABLED = True` in `config.py`.

Now utterances are labeled `Speaker_1`, `Speaker_2`, etc.

## Configuration

All tunable constants live in `config.py`:

| Constant | Default | Meaning |
| --- | --- | --- |
| `GEMINI_MODEL` | `gemini-1.5-pro` | Gemini model used for decisions |
| `SAMPLE_RATE` | `16000` | Audio sample rate (Hz), required by Whisper |
| `CHUNK_SECONDS` | `3` | Length of each captured audio chunk |
| `BUFFER_MAX_UTTERANCES` | `50` | Conversation turns kept in memory |
| `COOLDOWN_SECONDS` | `15` | Minimum gap between AI responses |
| `DIARIZATION_ENABLED` | `False` | Turn speaker diarization on/off |

## Common issues and fixes

- **Microphone not detected / PortAudio error**: ensure a microphone is
  connected and recognized by the OS. On Linux install `portaudio19-dev`. List
  devices with `python -c "import sounddevice as sd; print(sd.query_devices())"`.
- **`GEMINI_API_KEY is not set`**: copy `.env.example` to `.env` and add your key.
  The app validates this on startup and refuses to run without it.
- **Slow transcription**: Whisper runs on CPU by default. The `base` model is the
  fastest reasonable choice; increasing `CHUNK_SECONDS` reduces overhead per
  chunk. A CUDA-capable GPU greatly speeds up transcription.
- **No speech is heard from the assistant**: pyttsx3 needs a TTS backend. On
  Linux install `espeak-ng`; on macOS/Windows the system TTS is used.
- **Diarization fails to load**: confirm you accepted the model terms on
  HuggingFace and that `HUGGINGFACE_TOKEN` is valid. The app falls back to
  passthrough mode (`Speaker_Unknown`) automatically.
