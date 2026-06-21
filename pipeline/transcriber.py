# pipeline/transcriber.py
"""Phase 2: Transcribes raw audio chunks into text using OpenAI Whisper."""

import logging
import queue
import threading

import whisper

logger = logging.getLogger(__name__)


class Transcriber:
    """
    Pulls audio chunks from audio_queue, transcribes with Whisper,
    and puts non-empty text strings into text_queue.
    """

    def __init__(self, audio_queue: queue.Queue):
        self.audio_queue = audio_queue
        self.text_queue = queue.Queue()
        self._running = False
        self._thread = None
        # Load the model once at startup — never inside the loop.
        self.model = whisper.load_model("base")
        logger.info("Whisper model loaded.")

    def start(self):
        """Start the background transcription thread."""
        if self._running:
            logger.warning("Transcriber.start() called but transcriber is already running.")
            return

        self._running = True
        self._thread = threading.Thread(target=self._transcribe_loop, daemon=True)
        self._thread.start()
        logger.info("Transcriber started.")

    def stop(self):
        """Stop transcription and wait for the background thread to finish."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Transcriber stopped.")

    def _transcribe_loop(self):
        """
        Continuously reads audio from audio_queue and transcribes each chunk.

        For each chunk: call self.model.transcribe(audio_chunk, fp16=False),
        extract result["text"].strip(), and if non-empty put it into text_queue.
        A 1-second get() timeout lets the loop re-check self._running and exit
        cleanly when stopped. Failures on a single chunk are logged and skipped.
        """
        while self._running:
            try:
                audio_chunk = self.audio_queue.get(timeout=1)
            except queue.Empty:
                # No audio available right now — loop back and check _running.
                continue

            try:
                result = self.model.transcribe(audio_chunk, fp16=False)
                text = result["text"].strip()
                if text:
                    logger.info("Transcription: %s", text)
                    self.text_queue.put(text)
            except Exception as exc:  # noqa: BLE001 - skip bad chunks, never crash.
                logger.error("Whisper failed to transcribe a chunk: %s", exc)
