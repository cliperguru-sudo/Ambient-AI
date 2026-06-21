# utils/audio_output.py
"""Wraps pyttsx3 for speaking AI responses aloud."""

import logging

import pyttsx3

logger = logging.getLogger(__name__)


class AudioOutput:
    """Converts text to speech and plays it aloud using pyttsx3."""

    def __init__(self):
        self.engine = pyttsx3.init()
        # Set a natural speaking rate (words per minute).
        self.engine.setProperty("rate", 165)
        # Set volume (0.0 to 1.0).
        self.engine.setProperty("volume", 0.9)

    def speak(self, text: str):
        """Speak the given text aloud. Blocks until finished speaking."""
        logger.info("AI speaking: %s", text)
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as exc:  # noqa: BLE001 - audio failures must not crash.
            logger.error("Text-to-speech failed: %s", exc)
