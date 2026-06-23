# Deployment Guide for Ambient AI

## Quick Start (GitHub Actions)

### 1. Set Up GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and Variables → Actions):

| Secret Name | Value | Required | Source |
|-------------|-------|----------|--------|
| `GEMINI_API_KEY` | Your Gemini API key | ✅ Yes | https://ai.google.dev/ |
| `HUGGINGFACE_TOKEN` | HF token (optional) | ❌ No | https://huggingface.co/settings/tokens |

**Only GEMINI_API_KEY is required to make the system speak.**

### 2. Update Workflow File

In your `.github/workflows/deploy.yml` (or similar):

```yaml
name: Ambient AI Deployment

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Create .env file
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          HUGGINGFACE_TOKEN: ${{ secrets.HUGGINGFACE_TOKEN }}
        run: |
          cat > .env << EOF
          GEMINI_API_KEY=${GEMINI_API_KEY}
          HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN}
          EOF
      
      - name: Run tests
        run: python3 -m tests.test_trigger
      
      - name: Start application
        run: python3 main.py &
        # Note: Use & to run in background, or adjust for your deployment target
```

### 3. Verify Configuration

To verify the setup is correct without deploying:

```bash
# Clone repository
git clone <your-repo>
cd <repo>

# Verify .env loading
python3 -c "from config import GEMINI_API_KEY; print(f'API Key loaded: {bool(GEMINI_API_KEY)}')"
```

---

## Environment Variables Reference

### Required Variables

**GEMINI_API_KEY**
- **What**: Your Google Gemini API key
- **How to get**: 
  1. Visit https://ai.google.dev/
  2. Click "Get API Key" (top right)
  3. Create or select a Google Cloud project
  4. Copy the generated key
  5. Add to GitHub Secrets
- **Format**: String starting with `AIza...`
- **Why needed**: Enables AI decision-making on whether to speak

### Optional Variables

**HUGGINGFACE_TOKEN**
- **What**: HuggingFace API token for speaker diarization
- **How to get**: https://huggingface.co/settings/tokens
- **Required if**: You set `DIARIZATION_ENABLED = True` in config.py
- **Otherwise**: Leave empty (system uses passthrough mode)
- **Note**: Without this, all speakers labeled "Speaker_Unknown" (still works!)

---

## Configuration Files

### .env (Runtime - Never Commit!)

```
# .env
GEMINI_API_KEY=<your-key-here>
# HUGGINGFACE_TOKEN=<optional>
```

**⚠️ IMPORTANT**: Add `.env` to `.gitignore` - never commit secrets!

```bash
# Verify .env is ignored
echo ".env" >> .gitignore
git rm --cached .env 2>/dev/null
git add .gitignore
git commit -m "Ignore .env file"
```

### .env.example (Template - Safe to Commit)

```
# .env.example
GEMINI_API_KEY=your_gemini_api_key_here
HUGGINGFACE_TOKEN=your_huggingface_token_here
```

This shows team members what variables are needed without exposing secrets.

### config.py (Code - Safe to Commit)

All configurable values are in `config.py`:

```python
# Gemini AI Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")       # ← Reads from .env
GEMINI_MODEL = "gemini-2.5-flash"

# Audio Settings
SAMPLE_RATE = 16000                                # Hz
CHUNK_SECONDS = 3                                  # Duration per chunk

# Buffer Settings
BUFFER_MAX_UTTERANCES = 50                         # Memory size

# Trigger Behavior
COOLDOWN_SECONDS = 15                              # Min seconds between responses

# Speaker Diarization
DIARIZATION_ENABLED = False                        # Enable for multi-speaker
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
```

You can modify these values directly in `config.py` for different deployments.

---

## Troubleshooting

### Problem: "GEMINI_API_KEY is not set"

**Cause**: .env file is missing or empty

**Solution**:
```bash
# Check if .env exists
ls -la .env

# If missing, create it
echo "GEMINI_API_KEY=<your-key>" > .env

# Verify it loads
python3 -c "from config import GEMINI_API_KEY; print('✅ Loaded!' if GEMINI_API_KEY else '❌ Missing')"
```

### Problem: "API key not valid"

**Cause**: API key is incorrect or expired

**Solution**:
1. Go to https://ai.google.dev/
2. Generate a new API key
3. Update GitHub Secrets
4. Update local .env file
5. Re-deploy

### Problem: "Application transcribes but doesn't respond"

**Cause**: Either:
- Invalid API key (see above)
- Insufficient request quota on Gemini
- Network connectivity issue

**Debug**:
```bash
# Check logs for specific error
tail -f ambient_ai.log | grep "Decision:"

# Run test with debug output
python3 test_pipeline_integration.py
```

### Problem: Disk space errors during Whisper installation

**Cause**: Whisper model is ~1GB, not enough disk space

**Solution**:
- Use lightweight alternative or
- Use cloud-based transcription service
- Clean up disk space before install

---

## Production Deployment Tips

### 1. Use Cloud Secrets Manager

Instead of GitHub Secrets, consider:
- **AWS Secrets Manager**: `boto3` library
- **Google Cloud Secret Manager**: `google-cloud-secret-manager`
- **HashiCorp Vault**: `hvac` library

Example:
```python
# Load from AWS Secrets Manager
import boto3
client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='ambient-ai-key')
GEMINI_API_KEY = secret['SecretString']
```

### 2. Rate Limiting

Add exponential backoff for Gemini API calls:

```python
# pipeline/trigger.py
import time
from functools import wraps

def retry_with_backoff(max_retries=3, base_delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
                    else:
                        raise
        return wrapper
    return decorator

@retry_with_backoff()
def evaluate(self, formatted_transcript, latest_utterance):
    # ... existing code ...
```

### 3. Monitoring & Alerting

Log key metrics:

```python
# Track API calls
logger.info("API_CALL", extra={
    "timestamp": time.time(),
    "buffer_size": len(buffer),
    "decision": "INTERVENE" if response else "SILENT",
    "latency_ms": (time.time() - start) * 1000
})
```

### 4. Cost Management

Gemini API pricing:
- **Free tier**: Limited requests
- **Paid**: ~$0.075 per 1M input tokens, ~$0.30 per 1M output tokens

To keep costs low:
- Increase `COOLDOWN_SECONDS` (fewer API calls)
- Reduce `BUFFER_MAX_UTTERANCES` (shorter context)
- Filter trivial utterances before sending to API

### 5. Continuous Integration

Run tests before deployment:

```yaml
- name: Run all tests
  run: |
    python3 test_import.py
    python3 test_pipeline_integration.py
    python3 -m tests.test_trigger
```

---

## Deployment Checklist

Before deploying to production:

- [ ] GitHub Secrets configured (`GEMINI_API_KEY`)
- [ ] `.env` added to `.gitignore`
- [ ] `.env.example` in repository (shows required vars)
- [ ] All tests passing locally
- [ ] Tested with sample phrases
- [ ] Logs show correct decision flow
- [ ] Response quality verified with different conversation types
- [ ] Rate limiting configured (if needed)
- [ ] Monitoring/alerting set up
- [ ] Documentation updated
- [ ] Team members briefed on configuration

---

## Quick Reference

| Task | Command |
|------|---------|
| Check config | `python3 -c "from config import *; print(GEMINI_API_KEY[:10])"` |
| Run tests | `python3 test_pipeline_integration.py` |
| Start app | `python3 main.py` |
| View logs | `tail -f ambient_ai.log` |
| Generate new API key | Visit https://ai.google.dev/ |
| Update GitHub Secret | Settings → Secrets and Variables → Actions |

---

## Support

**If deployment fails**:
1. Check `ambient_ai.log` for error messages
2. Verify .env file exists and has valid API key
3. Run `python3 test_pipeline_integration.py` for diagnostics
4. Check GitHub Actions logs for environment setup issues
5. Refer to ANALYSIS.md for technical details

**Questions about Gemini API**:
- Documentation: https://ai.google.dev/tutorials/rest_quickstart
- Status Page: https://status.cloud.google.com/

