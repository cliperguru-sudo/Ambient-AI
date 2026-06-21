# pipeline/diarizer.py
"""Phase 3: Labels transcribed text with speaker identities (who said what)."""

import logging

from config import DIARIZATION_ENABLED, HUGGINGFACE_TOKEN, SAMPLE_RATE

logger = logging.getLogger(__name__)


class Diarizer:
    """
    Labels transcribed text with speaker identities.

    If DIARIZATION_ENABLED=False in config.py (or pyannote fails to load), it
    runs in passthrough mode and labels everything as "Speaker_Unknown".
    """

    def __init__(self):
        self.pipeline = None
        if DIARIZATION_ENABLED:
            try:
                from pyannote.audio import Pipeline

                self.pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=HUGGINGFACE_TOKEN,
                )
                logger.info("Diarization pipeline loaded.")
            except Exception as exc:  # noqa: BLE001 - degrade gracefully.
                logger.warning(
                    "Diarization failed to load: %s. Falling back to passthrough mode.",
                    exc,
                )
                self.pipeline = None

    def label(self, text: str, audio_chunk=None) -> dict:
        """
        Takes transcribed text and optionally the raw audio chunk.

        Returns: {"speaker": "Speaker_1", "text": "the text"}.
        If diarization is disabled or fails, speaker is "Speaker_Unknown".
        """
        # Passthrough mode: no pipeline or no audio to analyze.
        if self.pipeline is None or audio_chunk is None:
            return {"speaker": "Speaker_Unknown", "text": text}

        try:
            # pyannote expects a {"waveform": tensor[channel, time], "sample_rate": int} dict.
            import torch

            waveform = torch.from_numpy(audio_chunk).float().unsqueeze(0)
            diarization = self.pipeline({"waveform": waveform, "sample_rate": SAMPLE_RATE})

            # Pick the speaker who talks for the longest total duration in the chunk.
            speaker_durations = {}
            for segment, _, speaker in diarization.itertracks(yield_label=True):
                speaker_durations[speaker] = (
                    speaker_durations.get(speaker, 0.0) + segment.duration
                )

            if not speaker_durations:
                return {"speaker": "Speaker_Unknown", "text": text}

            dominant = max(speaker_durations, key=speaker_durations.get)
            # pyannote labels speakers as "SPEAKER_00" — normalize to "Speaker_1" style.
            speaker_label = _normalize_speaker_label(dominant)
            return {"speaker": speaker_label, "text": text}
        except Exception as exc:  # noqa: BLE001 - never crash the pipeline.
            logger.warning("Diarization failed on a chunk: %s. Using Speaker_Unknown.", exc)
            return {"speaker": "Speaker_Unknown", "text": text}


def _normalize_speaker_label(raw_label: str) -> str:
    """Convert a pyannote label like 'SPEAKER_00' into 'Speaker_1'."""
    try:
        index = int(raw_label.split("_")[-1])
        return f"Speaker_{index + 1}"
    except (ValueError, IndexError):
        return raw_label
