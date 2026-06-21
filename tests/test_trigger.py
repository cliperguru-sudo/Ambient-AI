# tests/test_trigger.py
"""Runs the intervention trigger against the sample transcripts.

This calls the real Gemini API (it requires GEMINI_API_KEY in your .env), so
it is an integration check rather than a unit test. The trigger's cooldown is
reset before each sample so back-to-back evaluations are not suppressed.
"""

import logging

from pipeline.trigger import InterventionTrigger
from tests.sample_transcripts import SAMPLES

logging.basicConfig(level=logging.INFO)


def run_tests():
    trigger = InterventionTrigger()
    passed = 0
    failed = 0

    for sample in SAMPLES:
        # Reset the cooldown so each sample is evaluated independently.
        trigger._last_spoke_at = 0.0

        result = trigger.evaluate(
            formatted_transcript=sample["transcript"],
            latest_utterance=sample["latest_utterance"],
        )
        did_intervene = result is not None

        status = "PASS" if did_intervene == sample["should_intervene"] else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1

        print(f"[{status}] {sample['name']}")
        print(f"       Expected intervene: {sample['should_intervene']}")
        print(f"       Actually intervened: {did_intervene}")
        if result:
            print(f"       Response: {result}")
        print(f"       Reason: {sample['reason']}\n")

    print(f"Results: {passed} passed, {failed} failed out of {len(SAMPLES)} tests.")


if __name__ == "__main__":
    run_tests()
