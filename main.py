# main.py
"""Phase 8: Entry point — wires every component into a single ambient loop."""

import logging
import queue
import time

from pipeline.audio_capture import AudioCapture
from pipeline.buffer import ConversationBuffer
from pipeline.diarizer import Diarizer
from pipeline.responder import Responder
from pipeline.transcriber import Transcriber
from pipeline.trigger import InterventionTrigger
from utils.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Ambient AI Assistant Starting ===")

    # Initialize all components.
    capture = AudioCapture()
    transcriber = Transcriber(audio_queue=capture.audio_queue)
    diarizer = Diarizer()
    buffer = ConversationBuffer()
    trigger = InterventionTrigger()
    responder = Responder()

    # Start background threads.
    capture.start()
    transcriber.start()

    logger.info("Listening... (press Ctrl+C to stop)")

    try:
        while True:
            # Step 1: Get the next transcribed text from the transcriber.
            try:
                text = transcriber.text_queue.get(timeout=1)
            except queue.Empty:
                continue

            # Wrap the per-utterance processing so one bad turn never breaks the loop.
            try:
                # Step 2: Label the speaker.
                labeled = diarizer.label(text)
                speaker = labeled["speaker"]
                utterance_text = labeled["text"]

                # Step 3: Add the labeled utterance to the buffer.
                buffer.add(speaker=speaker, text=utterance_text)

                # Step 4: Get the formatted transcript from the buffer.
                formatted_transcript = buffer.get_formatted_transcript()

                # Step 5: Ask the trigger if the AI should speak.
                response = trigger.evaluate(
                    formatted_transcript=formatted_transcript,
                    latest_utterance=utterance_text,
                )

                # Step 6: If the trigger returned a response, speak it.
                if response is not None:
                    responder.speak(response)
            except Exception as exc:  # noqa: BLE001 - keep the loop alive.
                logger.error("Error while processing an utterance: %s", exc)

            time.sleep(0.05)  # Tiny sleep to avoid busy-waiting.

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        capture.stop()
        transcriber.stop()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    main()
