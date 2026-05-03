# 🧪 Vera Bot - Complete Testing Guide

## Quick Start: Manual Testing

### Prerequisites
- Bot running locally: `python main.py` (or on Render: `https://your-render-url.onrender.com`)
- `curl` installed
- Port `8000` available (or set `PORT` environment variable)

---

## 📋 Manual Test Cases

### TEST 1: Health Check
**Purpose:** Verify bot is running and context is loaded  
**Endpoint:** `GET /v1/healthz`

```bash
curl -s http://localhost:8000/v1/healthz | python -m json.tool
```

**Expected Output:**
```json
{
  "status": "ok",
  "uptime_seconds": 3600,
  "contexts_loaded": {
    "category": 5,
    "merchant": 10,
    "customer": 0,
    "trigger": 25
  }
}
```

**Pass Criteria:**
- ✅ `status` == "ok"
- ✅ `uptime_seconds` > 0
- ✅ Response is valid JSON

---

### TEST 2: Metadata Check
**Purpose:** Verify bot configuration and model info  
**Endpoint:** `GET /v1/metadata`

```bash
curl -s http://localhost:8000/v1/metadata | python -m json.tool
```

**Expected Output:**
```json
{
  "team_name": "Vera",
  "team_members": ["Abhishek"],
  "model": "gpt-3.5-turbo",
  "approach": "Signal ranker + grounded composer + reply handler",
  "version": "1.0.0"
}
```

**Pass Criteria:**
- ✅ `team_name` == "Vera"
- ✅ `model` contains "gpt-3.5" or "gpt-4"
- ✅ All fields present

---

### TEST 3: Positive Intent (Explicit Accept)
**Purpose:** Test reply handler detects strong positive signals  
**Endpoint:** `POST /v1/reply`

```bash
curl -s -X POST http://localhost:8000/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "Yes, absolutely! Let'"'"'s do it.", "conversation_id": "conv_001"}'
```

**Expected Output:**
```json
{
  "action": "send",
  "body": "Excellent! I'm setting this up now. You'll see results in your dashboard within 2 hours.",
  "rationale": "High intent signal detected",
  "confidence": 0.95,
  "reason_code": "explicit_accept"
}
```

**Pass Criteria:**
- ✅ `action` == "send"
- ✅ `reason_code` == "explicit_accept"
- ✅ `confidence` >= 0.8
- ✅ Response body contains confirmation message

---

### TEST 4: Negative Intent (Explicit Decline)
**Purpose:** Test reply handler detects strong negative signals  
**Endpoint:** `POST /v1/reply`

```bash
curl -s -X POST http://localhost:8000/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "No, I'"'"'m not interested.", "conversation_id": "conv_002"}'
```

**Expected Output:**
```json
{
  "action": "end",
  "body": "No problem! I'll check back with you later. Reach out if plans change.",
  "rationale": "Merchant declined opportunity",
  "confidence": 0.95,
  "reason_code": "explicit_decline"
}
```

**Pass Criteria:**
- ✅ `action` == "end"
- ✅ `reason_code` == "explicit_decline"
- ✅ `confidence` >= 0.8
- ✅ Response body is polite and non-pushy

---

### TEST 5: Unclear Intent (Needs Clarification)
**Purpose:** Test reply handler asks for more info when intent is ambiguous  
**Endpoint:** `POST /v1/reply`

```bash
curl -s -X POST http://localhost:8000/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me more about this.", "conversation_id": "conv_003"}'
```

**Expected Output:**
```json
{
  "action": "send",
  "body": "Sounds like you want to learn more! What specific aspect interests you most—customer acquisition, retention, or seasonal demand?",
  "rationale": "Unclear intent; needs clarification",
  "confidence": 0.4,
  "reason_code": "unclear_intent"
}
```

**Pass Criteria:**
- ✅ `action` == "send"
- ✅ `reason_code` == "unclear_intent"
- ✅ `confidence` < 0.7
- ✅ Body asks clarifying questions

---

### TEST 6: Empty Message
**Purpose:** Test bot handles empty/null input gracefully  
**Endpoint:** `POST /v1/reply`

```bash
curl -s -X POST http://localhost:8000/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "", "conversation_id": "conv_004"}'
```

**Expected Output:**
```json
{
  "action": "send",
  "body": "Sounds like you want to learn more! What specific aspect interests you most—customer acquisition, retention, or seasonal demand?",
  "rationale": "Unclear intent; needs clarification",
  "confidence": 0.4,
  "reason_code": "unclear_intent"
}
```

**Pass Criteria:**
- ✅ No error/crash
- ✅ `action` == "send" (with clarification)
- ✅ `reason_code` == "unclear_intent"

---

### TEST 7: Case Insensitive Matching
**Purpose:** Verify intent detection works with various cases  
**Endpoint:** `POST /v1/reply`

```bash
curl -s -X POST http://localhost:8000/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "YeS", "conversation_id": "conv_005"}'
```

**Expected Output:**
```json
{
  "action": "send",
  "reason_code": "explicit_accept",
  "confidence": 0.95,
  "body": "Excellent! I'm setting this up now..."
}
```

**Pass Criteria:**
- ✅ `reason_code` == "explicit_accept" (despite "YeS" being mixed case)
- ✅ `confidence` >= 0.8

---

### TEST 8: Weighted Scoring (Multiple Signals)
**Purpose:** Test that bot accumulates signals from multiple words  
**Endpoint:** `POST /v1/reply`

```bash
curl -s -X POST http://localhost:8000/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "Yeah, I'"'"'m interested! Let'"'"'s go.", "conversation_id": "conv_006"}'
```

**Expected Output:**
```json
{
  "action": "send",
  "reason_code": "explicit_accept",
  "confidence": 0.95,
  "body": "Excellent! I'm setting this up now..."
}
```

**Pass Criteria:**
- ✅ `confidence` == 0.95 (max confidence due to multiple positive signals)
- ✅ `reason_code` == "explicit_accept"

---

### TEST 9: Mild Negative (Medium Confidence)
**Purpose:** Test confidence scaling with weak negative  
**Endpoint:** `POST /v1/reply`

```bash
curl -s -X POST http://localhost:8000/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "Maybe later.", "conversation_id": "conv_007"}'
```

**Expected Output:**
```json
{
  "action": "end",
  "reason_code": "explicit_decline",
  "confidence": 0.65,
  "body": "No problem! I'll check back with you later. Reach out if plans change."
}
```

**Pass Criteria:**
- ✅ `reason_code` == "explicit_decline" (mild negative)
- ✅ `0.6 <= confidence <= 0.8` (medium confidence)

---

### TEST 10: Trigger Ranking (Context Processing)
**Purpose:** Verify /v1/tick processes triggers by urgency  
**Endpoint:** `POST /v1/tick`

```bash
curl -s -X POST http://localhost:8000/v1/tick \
  -H "Content-Type: application/json" \
  -d '{"available_triggers": ["trg_001", "trg_002", "trg_003"]}'
```

**Expected Output:**
```json
{
  "actions": [
    {
      "merchant_id": "m_001",
      "trigger_id": "trg_001",
      "body": "We see...",
      "cta": "open_ended",
      "suppression_key": "trg_001:m_001"
    }
  ]
}
```

**Pass Criteria:**
- ✅ Response is array of actions
- ✅ Each action has `merchant_id`, `trigger_id`, `body`, `cta`, `suppression_key`
- ✅ Messages are category-specific

---

### TEST 11: Message Quality (Category-Aware)
**Purpose:** Verify messages contain category-specific language  
**Endpoint:** `POST /v1/context` then `POST /v1/tick`

```bash
# First, store merchant context with category
curl -s -X POST http://localhost:8000/v1/context \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "merchant",
    "context_id": "m_test_001",
    "version": "1.0",
    "payload": {
      "merchant_id": "m_test_001",
      "category_slug": "restaurants",
      "name": "Test Restaurant"
    }
  }'

# Then process trigger
curl -s -X POST http://localhost:8000/v1/tick \
  -H "Content-Type: application/json" \
  -d '{"available_triggers": ["trg_test_001"]}'
```

**Expected Output:**
- Restaurant message with terms like: "covers", "ambiance", "reservation"
- Dentist message would include: "appointments", "patients"
- Gym message would include: "members", "fitness"

**Pass Criteria:**
- ✅ Message contains category-appropriate keywords
- ✅ Tone matches business type (professional for dentists, casual for gyms)

---

### TEST 12: Error Resilience
**Purpose:** Verify bot handles malformed input gracefully  
**Endpoint:** `POST /v1/reply`

```bash
# Malformed JSON (missing message field)
curl -s -X POST http://localhost:8000/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "conv_008"}'
```

**Expected Output:**
- HTTP 422 Validation Error OR
- Bot returns safe default message

**Pass Criteria:**
- ✅ No 500 server error
- ✅ Clear error message or graceful fallback
- ✅ Bot continues to accept new requests

---

## 📊 Scoring & Confidence Explained

### Confidence Calculation
```
Score = sum(positive_weights) - sum(negative_weights)

confidence = min(0.95, 0.5 + (score × 0.15))
```

### Keyword Weights
**Positive Signals (3 pts):** "yes", "yeah", "absolutely", "definitely", "let's do it", "yep"  
**Positive Signals (2 pts):** "ok", "sure", "go", "great", "interested", "good"  
**Negative Signals (3 pts):** "no", "nope", "stop", "not interested"  
**Negative Signals (2 pts):** "not", "don't", "can't", "skip"  
**Negative Signals (1 pt):** "later", "busy", "maybe"

### Examples
| Message | Score | Confidence | Action | Reason |
|---------|-------|-----------|--------|--------|
| "Yes!" | +3 | 0.95 | send | explicit_accept |
| "No, thanks" | -3 | 0.05 | end | explicit_decline |
| "Maybe later" | -1 | 0.35 | end | explicit_decline |
| "Tell me more" | 0 | 0.50 | send | unclear_intent |
| "" | 0 | 0.40 | send | unclear_intent |

---

## 🚀 Automated Testing with Pytest

Run the full test suite:
```bash
cd vera-ai-challenge/vera-bot
pytest test_improvements.py -v
```

**Coverage:**
- ✅ 9 reply handler tests (intent detection, confidence, reason codes)
- ✅ 12 category expansion tests (all categories supported)
- ✅ 5 error handling tests (graceful degradation)
- ✅ 5 message quality tests (personalization, tone)
- ✅ 5 integration tests (end-to-end flows)
- **Total: 40+ test cases**

---

## 🐛 Troubleshooting

### "Connection refused" on port 8000
```bash
# Check if port is already in use
lsof -i :8000

# Or use different port
PORT=8001 python main.py
```

### "No module named 'openai'"
```bash
pip install -r vera-bot/requirements.txt
```

### "OPENAI_API_KEY not found"
```bash
cd vera-bot
echo "OPENAI_API_KEY=sk_your_key_here" > .env
cd ..
python main.py
```

### "Expecting value: line 1 column 1" (empty response)
- Bot may not be running (test with `curl http://localhost:8000/v1/healthz`)
- Check local terminal or Render logs for errors
- Verify firewall isn't blocking port 8000

### Tests fail with import errors
```bash
# Reinstall dependencies
deactivate
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r vera-bot/requirements.txt
pytest vera-bot/test_improvements.py -v
```

---

## 📈 Test Execution Flow

```
START
  ↓
[TEST 1] Health Check
  ↓
[TEST 2] Metadata
  ↓
[TEST 3-9] Reply Handler
  ├─ Positive Intent
  ├─ Negative Intent
  ├─ Unclear Intent
  ├─ Empty Message
  ├─ Case Insensitive
  ├─ Multiple Signals
  └─ Medium Confidence
  ↓
[TEST 10] Trigger Ranking
  ↓
[TEST 11] Category-Aware Messages
  ↓
[TEST 12] Error Resilience
  ↓
END: All passed!
```

---

## 🎯 Success Criteria

For challenge submission, bot should:
- ✅ Respond to `/v1/healthz` and `/v1/metadata` correctly
- ✅ Rank triggers by urgency and compose personalized messages
- ✅ Classify responses with intent (accept/decline/clarify)
- ✅ Provide confidence scores (0-1 scale)
- ✅ Handle edge cases gracefully
- ✅ Support 12+ merchant categories
- ✅ Stay running for 3+ days without crashing

---

## 📝 Before Submission

1. Run all 12 manual tests → All pass ✅
2. Run `pytest test_improvements.py -v` → All 40+ tests pass ✅
3. Check Render logs → No critical errors ✅
4. Test live bot URL → All endpoints responsive ✅

---

## 📞 Support

- **Local testing issues?** Check TESTING.md troubleshooting
- **Code questions?** Read main.py comments
- **Dependency issues?** Verify requirements.txt matches your environment

