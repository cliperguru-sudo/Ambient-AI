# pipeline/audio_capture.py
"""Phase 1: Continuously captures raw microphone audio in fixed-length chunks."""

import logging
import queue
import threading

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHUNK_SECONDS = 3


class AudioCapture:
    """
    Captures audio from the microphone in 3-second chunks.

    Puts each chunk into self.audio_queue for the transcriber to consume.
    Runs in a background thread — call start() to begin capturing.
    """

    def __init__(self):
        self.audio_queue = queue.Queue()
        self._running = False
        self._thread = None

    def start(self):
        """Start background audio capture thread."""
        if self._running:
            logger.warning("AudioCapture.start() called but capture is already running.")
            return

        self._running = True
        # Daemon thread so it dies automatically when the main program exits.
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Audio capture started (sample_rate=%d Hz, chunk=%ds).", SAMPLE_RATE, CHUNK_SECONDS)

    def stop(self):
        """Stop audio capture and wait for the background thread to finish."""
        self._running = False
        if self._thread is not None:
            # Give the thread up to one chunk-duration to wind down cleanly.
            self._thread.join(timeout=CHUNK_SECONDS + 1)
            self._thread = None
        logger.info("Audio capture stopped.")

    def _capture_loop(self):
        """
        Main loop: records CHUNK_SECONDS of audio, converts to a float32 numpy
        array normalized to [-1.0, 1.0], and puts it into self.audio_queue.

        Runs until self._running is False. Any error on a single recording is
        logged and skipped so the loop never crashes the program.
        """
        frames = int(SAMPLE_RATE * CHUNK_SECONDS)

        while self._running:
            try:
                # Record a single mono chunk as float32 in the range [-1.0, 1.0].
                recording = sd.rec(
                    frames,
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype="float32",
                )
                sd.wait()  # Block until this chunk has finished recording.

                # Flatten (frames, 1) -> (frames,) so Whisper receives a 1-D array.
                audio_chunk = np.squeeze(recording).astype(np.float32)
                self.audio_queue.put(audio_chunk)
            except Exception as exc:  # noqa: BLE001 - never let the loop die.
                logger.error(
                    "Audio capture failed (is a microphone connected?): %s", exc
                )
                # Briefly mark not-running on hard failure so we don't spin hot.
                if "PortAudio" in str(exc) or "device" in str(exc).lower():
                    logger.error("No usable microphone found — stopping capture loop.")
                    self._running = False
