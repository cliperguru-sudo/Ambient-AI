# pipeline/responder.py
"""Phase 6: Speaks the AI's response aloud."""

import logging

from utils.audio_output import AudioOutput

logger = logging.getLogger(__name__)


class Responder:
    """Takes a response string and speaks it aloud."""

    def __init__(self):
        self.audio_output = AudioOutput()

    def speak(self, response_text: str):
        """Speak the response. Logs before and after."""
        logger.info("Responder triggered with: '%s'", response_text)
        self.audio_output.speak(response_text)
        logger.info("Responder finished speaking.")
