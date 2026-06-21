# config.py
"""Central configuration for the Ambient Conversational AI assistant.

Every constant used across the project is defined here so there is a single
source of truth. Secrets (API keys / tokens) are read from a .env file via
python-dotenv.
"""

import os

from dotenv import load_dotenv

# Load environment variables from a local .env file (if present) so the
# constants below can pick up secrets without them being committed to git.
load_dotenv()

# --- Gemini AI Settings ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")       # Required
GEMINI_MODEL = "gemini-1.5-pro"                     # Do not change

# --- Audio Settings ---
SAMPLE_RATE = 16000                                # Hz — required by Whisper
CHUNK_SECONDS = 3                                  # Duration of each audio chunk

# --- Buffer Settings ---
BUFFER_MAX_UTTERANCES = 50                         # Max conversation turns to remember

# --- Trigger Behavior ---
COOLDOWN_SECONDS = 15                              # Min seconds between AI responses

# --- Speaker Diarization ---
DIARIZATION_ENABLED = False                        # Set True only if pyannote is set up
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")  # Required only if DIARIZATION_ENABLED=True

# --- Validation ---
if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY is not set in your .env file.")
if DIARIZATION_ENABLED and not HUGGINGFACE_TOKEN:
    raise EnvironmentError("HUGGINGFACE_TOKEN must be set when DIARIZATION_ENABLED=True.")
