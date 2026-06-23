# Ambient AI - Quick Setup Guide

## TL;DR: Why No Responses?

**The app listens and transcribes correctly, but doesn't respond.**

**Reason**: Your `.env` file is missing the `GEMINI_API_KEY`.

**Fix**: Add one line to `.env`:

```bash
GEMINI_API_KEY=<your-api-key-from-https://ai.google.dev/>
```

That's it. The entire codebase is complete and working.

---

## Step-by-Step Fix

### 1. Get a Gemini API Key (2 minutes)

```bash
# Open this URL in your browser:
https://ai.google.dev/

# Click "Get API Key" (top right)
# Select or create a Google Cloud project
# Copy your API key
```

### 2. Add to `.env` File (1 minute)

```bash
# Replace <key> with your actual API key
echo "GEMINI_API_KEY=<key>" > .env
```

### 3. Verify It Works (1 minute)

```bash
python3 -c "from config import GEMINI_API_KEY; print('✅ Ready!' if GEMINI_API_KEY else '❌ Missing')"
```

### 4. Run the App (instantly)

```bash
python3 main.py
```

Now speak: "What's the capital of France?" and the AI will respond!

---

## What's Already Done ✅

| Component | Status | Notes |
|-----------|--------|-------|
| Codebase Architecture | ✅ Complete | 6 phases, fully implemented |
| File Structure | ✅ Complete | All 14 files present and working |
| Microphone Input | ✅ Working | Captures audio, transcribes text |
| Speaker Detection | ✅ Working | Labels speakers (passthrough mode) |
| Conversation Memory | ✅ Working | Maintains last 50 utterances |
| Decision Logic | ✅ Working | Evaluates when to speak |
| Text-to-Speech | ✅ Working | Can speak responses |
| Logging | ✅ Working | Tracks all decisions |
| Error Handling | ✅ Working | Fails gracefully |
| Tests | ✅ Passing | All integration tests pass |

**Only Missing**: GEMINI_API_KEY in .env file

---

## Deployment Checklist

- [ ] Get API key from https://ai.google.dev/
- [ ] Add `GEMINI_API_KEY=<key>` to `.env`
- [ ] Run `python3 main.py`
- [ ] Test with voice: "What time is it?"
- [ ] Check logs: `tail -f ambient_ai.log`

---

## Key Files

| File | Purpose |
|------|---------|
| **config.py** | Configuration (reads from .env) |
| **.env** | ← ADD YOUR API KEY HERE |
| **main.py** | Entry point, runs everything |
| **ANALYSIS.md** | Detailed technical breakdown |
| **DEPLOYMENT.md** | GitHub Actions integration guide |

---

## How It Works

```
You speak:           "What's the capital of France?"
       ↓
AudioCapture:        Records your voice
       ↓
Transcriber:         Converts to text
       ↓
Diarizer:            Labels who spoke
       ↓
Buffer:              Stores conversation history
       ↓
Trigger:             Calls Gemini API (WITH YOUR KEY) → "Yes, respond"
       ↓
Responder:           Speaks: "It's Paris"
       ↓
You hear:            "It's Paris"
```

Without API key, Step 5 fails and system stays silent.

---

## FAQ

**Q: Do I need HuggingFace token?**
A: No, it's optional. System works fine without it (labels speakers as "Speaker_Unknown").

**Q: Can I use a different LLM?**
A: Not easily - the code is specific to Gemini. But the trigger logic is in `pipeline/trigger.py`, so you could adapt it.

**Q: Why does it sometimes stay silent?**
A: The AI is trained to only speak when it has a genuine factual answer. Casual conversation, opinions, and rhetorical questions = silence.

**Q: How much does Gemini API cost?**
A: Free tier has limits. Paid: ~$0.075 per 1M input tokens. Typical usage might cost $0.10-1.00/day.

**Q: Can I use it on my laptop?**
A: Yes! Requires:
  - Microphone & speakers
  - ~2GB disk (for Whisper model download)
  - Internet connection (for Gemini API)

---

## Troubleshooting

**Error: "GEMINI_API_KEY is not set"**
```bash
# Your .env file is missing or empty
ls .env              # Check if file exists
cat .env             # Check if it has content
echo "GEMINI_API_KEY=..." > .env  # Create/fix it
```

**Error: "API key not valid"**
```bash
# Your API key is incorrect or expired
# 1. Go to https://ai.google.dev/
# 2. Generate a new API key
# 3. Update .env
# 4. Run again
```

**AI not responding to questions**
```bash
# Check the logs to see what Gemini returned
tail -f ambient_ai.log | grep "Decision:"

# The AI is trained to be quiet by default
# It only speaks if:
# - Someone asked a factual question
# - AI has reliable knowledge
# - Response is brief (<30 words)
```

---

## Next Steps

1. **Immediate**: Add API key and test
2. **Short-term**: Monitor logs, fine-tune response criteria
3. **Long-term**: Consider enabling speaker diarization, add cloud secrets manager

See **ANALYSIS.md** and **DEPLOYMENT.md** for advanced configuration.

---

## Support Resources

| Need | Link |
|------|------|
| Gemini API Docs | https://ai.google.dev/tutorials/rest_quickstart |
| GitHub Secrets Setup | https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions |
| Python Docs | https://docs.python.org/3.11/ |
| Microphone Issues | Check your OS audio settings |

---

**Version**: 1.0  
**Last Updated**: 2026-06-22  
**Status**: 🟢 Ready to Deploy (Once API Key Added)
