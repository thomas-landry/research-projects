---
description: Security constraints for API keys, secrets, and terminal command safety
---

# Security Rules

## 1. Secrets Management

| Rule | Implementation |
|------|----------------|
| **Environment Variables Only** | All API keys, passwords, and tokens MUST be loaded via `python-dotenv` from `.env` |
| **No Hardcoding** | Never output credentials in source code, test files, or logs |
| **Audit Log Safety** | Never log API keys or bearer tokens to JSONL audit files |

### Required Pattern
```python
# ✅ Correct
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

# ❌ Forbidden
api_key = "sk-or-v1-abc123..."
```

---

## 2. Terminal Command Safety

### Whitelisted Commands (Safe to Auto-Run)
```
pytest, python -m pytest, git status, git diff, git log
ls, cat, head, tail, grep, find, wc
pip list, pip show
```

### Blocked Commands (NEVER Auto-Run)
```
rm -rf, rm -r, rmdir
curl | bash, wget | sh
pip install (without user approval)
git push, git commit
chmod, chown
sudo anything
```

---

## 3. Data Privacy

- Do NOT log patient-identifiable information from medical papers
- Extracted data should use de-identified references (e.g., "Patient 1", "Case A")
- Vector store queries should not expose raw PHI in responses
