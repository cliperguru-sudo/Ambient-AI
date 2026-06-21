# pipeline/trigger.py
"""Phase 5: The intervention trigger — decides IF and WHAT the AI should say.

This is the most important module in the project. After every new utterance it
asks Gemini whether the AI should speak. The default state is always SILENCE:
on cooldown, on any API failure, on an unparseable response, or on ambiguity,
the trigger returns None (stay quiet).
"""

import logging
import time

import google.generativeai as genai

from config import COOLDOWN_SECONDS, GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT_TEMPLATE = """
You are an ambient AI assistant silently listening to a conversation between people.
Your role is like a knowledgeable friend in the room — you almost never speak,
but when you do, it is because you can genuinely help with a specific factual need.

Here is the conversation so far:
---
{formatted_transcript}
---

The most recent thing said was:
"{latest_utterance}"

Decide if you should speak right now. Respond with EXACTLY one of:
1. The word SILENT (if you should not speak)
2. INTERVENE: followed by your response (if you should speak)

You should ONLY intervene when ALL of these are true:
- Someone asked a question that went unanswered OR expressed uncertainty about a fact
- You have reliable knowledge that directly answers their question
- Your response would be brief (under 30 words)
- The moment is right — they are not mid-sentence or mid-thought

You should NEVER intervene for:
- Opinions or personal preferences
- Emotional topics or sensitive conversations
- Rhetorical questions
- Things already resolved in the conversation
- Small talk or filler phrases
- Any topic where you are not certain of the answer

Your response if intervening must be natural, spoken aloud, extremely brief,
like a person casually answering. Do not say "As an AI" or introduce yourself.
Just give the answer naturally, the way a knowledgeable friend would say it mid-conversation.

Respond now with SILENT or INTERVENE: [your response]
"""


class InterventionTrigger:
    """
    After each new utterance, evaluates whether the AI should speak.

    Returns None if it should stay silent, or a string response if it should
    speak. Enforces a cooldown so the AI cannot chatter.
    """

    def __init__(self):
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self._last_spoke_at = 0.0  # Unix timestamp of last intervention

    def evaluate(self, formatted_transcript: str, latest_utterance: str):
        """
        Calls Gemini with the full conversation context.

        Returns the response string if the AI should speak, or None if it
        should stay silent. Fails safe to silence on any error.
        """
        # 1. Cooldown — stay silent if we spoke too recently.
        seconds_since_last = time.time() - self._last_spoke_at
        if seconds_since_last < COOLDOWN_SECONDS:
            logger.info(
                "Decision: SILENT (cooldown active, %.1fs of %ds elapsed).",
                seconds_since_last,
                COOLDOWN_SECONDS,
            )
            return None

        # 2. Build the prompt.
        prompt = SYSTEM_PROMPT_TEMPLATE.format(
            formatted_transcript=formatted_transcript,
            latest_utterance=latest_utterance,
        )

        # 3. Call Gemini. Any failure -> default to silence.
        try:
            response = self.model.generate_content(prompt)
            raw_text = (response.text or "").strip()
        except Exception as exc:  # noqa: BLE001 - never crash; stay silent.
            logger.error("Gemini API call failed: %s. Defaulting to SILENT.", exc)
            return None

        # 4/5/6/7. Parse the response.
        if raw_text.upper().startswith("INTERVENE:"):
            # Extract everything after the first colon and clean it up.
            response_text = raw_text.split(":", 1)[1].strip()
            if not response_text:
                logger.warning("Got INTERVENE with empty body. Defaulting to SILENT.")
                return None
            self._last_spoke_at = time.time()
            logger.info("Decision: INTERVENE -> %s", response_text)
            return response_text

        if raw_text.upper() == "SILENT":
            logger.info("Decision: SILENT (model chose silence).")
            return None

        # Anything else is unexpected — fail safe to silence.
        logger.warning(
            "Unexpected model response (defaulting to SILENT): %r", raw_text
        )
        return None
