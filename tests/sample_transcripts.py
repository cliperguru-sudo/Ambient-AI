# tests/sample_transcripts.py
"""Sample conversations used to exercise the intervention trigger logic.

Each sample declares whether the AI SHOULD intervene and why, so the test
runner can compare the model's decision against the expected behavior.
"""

SAMPLES = [
    {
        "name": "World Cup question - should intervene",
        "transcript": "[Speaker_1]: I think Argentina is playing tonight.\n[Speaker_2]: Are they? I'm not sure when they play.",  # noqa: E501
        "latest_utterance": "Are they? I'm not sure when they play.",
        "should_intervene": True,
        "reason": "Speaker_2 expressed direct factual uncertainty",
    },
    {
        "name": "Opinion discussion - should stay silent",
        "transcript": "[Speaker_1]: I think Messi is better than Ronaldo.\n[Speaker_2]: No way, Ronaldo is clearly better.",  # noqa: E501
        "latest_utterance": "No way, Ronaldo is clearly better.",
        "should_intervene": False,
        "reason": "Pure opinion debate, no factual gap",
    },
    {
        "name": "Rhetorical question - should stay silent",
        "transcript": "[Speaker_1]: Why does time go so fast when you're having fun?",
        "latest_utterance": "Why does time go so fast when you're having fun?",
        "should_intervene": False,
        "reason": "Rhetorical, not a genuine information request",
    },
    {
        "name": "Factual gap mid-conversation - should intervene",
        "transcript": "[Speaker_1]: What's the capital of Australia again? I always mix it up.\n[Speaker_2]: I think it's Sydney?",  # noqa: E501
        "latest_utterance": "I think it's Sydney?",
        "should_intervene": True,
        "reason": "Incorrect factual claim (it's Canberra) — AI should gently correct",
    },
    {
        "name": "Emotional conversation - should stay silent",
        "transcript": "[Speaker_1]: I'm just really stressed about work lately.\n[Speaker_2]: I know, it sounds really tough.",  # noqa: E501
        "latest_utterance": "I know, it sounds really tough.",
        "should_intervene": False,
        "reason": "Emotional support conversation — AI must not insert itself",
    },
]
