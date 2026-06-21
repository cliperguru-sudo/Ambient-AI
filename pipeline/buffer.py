# pipeline/buffer.py
"""Phase 4: Rolling conversation buffer — the AI's short-term memory."""

import logging
import time
from collections import deque

from config import BUFFER_MAX_UTTERANCES

logger = logging.getLogger(__name__)


class ConversationBuffer:
    """
    Rolling window of the last BUFFER_MAX_UTTERANCES utterances.

    Each utterance: {"speaker": str, "text": str, "timestamp": float}.
    Backed by collections.deque(maxlen=...), so the oldest utterance is
    automatically discarded once the buffer is full.
    """

    def __init__(self):
        self._buffer = deque(maxlen=BUFFER_MAX_UTTERANCES)

    def add(self, speaker: str, text: str):
        """Add a new utterance. Automatically timestamps it."""
        utterance = {"speaker": speaker, "text": text, "timestamp": time.time()}
        self._buffer.append(utterance)
        logger.info("Buffer add [%s]: %s (size=%d)", speaker, text, len(self._buffer))

    def get_formatted_transcript(self) -> str:
        """
        Returns all buffered utterances as a formatted conversation string.

        Each line: [SpeakerName]: their text
        If the buffer is empty, returns an empty string.
        """
        if not self._buffer:
            return ""
        lines = [f"[{u['speaker']}]: {u['text']}" for u in self._buffer]
        return "\n".join(lines)

    def clear(self):
        """Reset the buffer to empty."""
        self._buffer.clear()

    def __len__(self):
        return len(self._buffer)
