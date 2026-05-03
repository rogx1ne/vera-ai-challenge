# VERA BOT: QUICK REFERENCE & TEST COMMANDS

## Test Endpoints As You Build

**Start bot:** `python main.py`

---

## 1. TEST HEALTHZ
```bash
curl http://localhost:8000/v1/healthz
```

**Expected response:**
```json
{
  "status": "ok",
  "uptime_seconds": 3600,
  "contexts_loaded": {
    "category": 0,
    "merchant": 0,
    "customer": 0,
    "trigger": 0
  }
}
```

---

## 2. TEST METADATA
```bash
curl http://localhost:8000/v1/metadata
```

**Expected response:**
```json
{
  "team_name": "Your Team Name",
  "team_members": ["Your Name"],
  "model": "claude-opus-4-20250514",
  "approach": "Signal ranker + grounded composer",
  "version": "1.0.0"
}
```

---

## 3. TEST /context (Store data)
```bash
curl -X POST http://localhost:8000/v1/context \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "merchant",
    "context_id": "m_001_drmeera",
    "version": 1,
    "payload": {
      "name": "Dr. Meera",
      "category": "dentists",
      "performance_score": 4.5,
      "offers": ["Dental Cleaning @ ₹299"],
      "reply_rate": 0.65
    }
  }'
```

**Expected response:**
```json
{
  "accepted": true,
  "ack_id": "ack_m_001_drmeera_1",
  "stored_at": "2026-05-02T..."
}
```

---

## 4. TEST /tick (Send messages)
```bash
curl -X POST http://localhost:8000/v1/tick \
  -H "Content-Type: application/json" \
  -d '{
    "now": "2026-05-02T10:30:00Z",
    "available_triggers": ["trg_research_digest_dentists"]
  }'
```

**Expected response:**
```json
{
  "actions": [
    {
      "merchant_id": "m_001_drmeera",
      "trigger_id": "trg_research_digest_dentists",
      "body": "Dr. Meera, 190 people in your area searched for 'Dental Check Up' this week. Your ₹299 offer is competitive. Should I send them a message?",
      "cta": "open_ended",
      "suppression_key": "trg_research_digest_dentists:m_001_drmeera"
    }
  ]
}
```

**Red flags:**
- ❌ Body is generic ("Hi, want to run a campaign?")
- ❌ Numbers are made up (not from expanded/ data)
- ❌ No specific offer mentioned
- ✅ Body has a specific number AND an offer

---

## 5. TEST /reply (Handle responses)
```bash
curl -X POST http://localhost:8000/v1/reply \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_001",
    "from_role": "merchant",
    "message": "Yes, send them the message",
    "turn_number": 2
  }'
```

**Expected response:**
```json
{
  "action": "send",
  "body": "Perfect! I'm drafting the message now. Check your dashboard in a minute.",
  "rationale": "Merchant accepted"
}
```

**Valid action values:**
- `"send"` - Send next message
- `"wait"` - Wait for follow-up
- `"end"` - End conversation

---

## Testing Locally (Before Deploy)

### Step 1: Start bot in Terminal 1
```bash
source venv/bin/activate
python main.py
```

**Should see:**
```
✓ All data loaded successfully
Uvicorn running on http://127.0.0.1:8000
```

### Step 2: Test in Terminal 2
```bash
# Copy-paste commands from above

# Quick test all endpoints
curl http://localhost:8000/v1/healthz | python -m json.tool
curl http://localhost:8000/v1/metadata | python -m json.tool

# Test context storage
curl -X POST http://localhost:8000/v1/context \
  -H "Content-Type: application/json" \
  -d '{"scope":"merchant","context_id":"test","version":1,"payload":{"name":"Test"}}'

# Test tick endpoint
curl -X POST http://localhost:8000/v1/tick \
  -H "Content-Type: application/json" \
  -d '{"available_triggers":["trg_test"]}'
```

---

## Testing After Deploy on Render

Replace `http://localhost:8000` with your Render URL:

```bash
# Example: https://vera-bot-xyz.onrender.com

curl https://vera-bot-xyz.onrender.com/v1/healthz
curl https://vera-bot-xyz.onrender.com/v1/metadata

# Full test
curl -X POST https://vera-bot-xyz.onrender.com/v1/tick \
  -H "Content-Type: application/json" \
  -d '{"available_triggers":["trg_research_digest_dentists"]}'
```

---

## Running Judge Simulator

```bash
# Make sure judge_simulator.py is in your vera-bot/ folder
# Edit it to set: BOT_URL, LLM_PROVIDER, LLM_API_KEY

python judge_simulator.py
```

**Output will show:**
```
Test case 1/30...
  Decision quality: 7/10
  Specificity: 8/10
  Category fit: 7/10
  Merchant fit: 6/10
  Engagement: 7/10
  Average: 7.0

Overall average across 30 tests: 7.2/10
```

**Target:** 7+ on each dimension

---

## Common Issues & Fixes

### "Name 'contexts' is not defined"
→ Make sure you're using the full code template, not partial code

### "Timeout error (30s)"
→ Claude API is slow. Reduce max_tokens from 150 to 80.
```python
message = client.messages.create(
    model="claude-opus-4-20250514",
    max_tokens=80,  # ← Change this
    ...
)
```

### "ANTHROPIC_API_KEY not found"
→ Check:
1. `.env` file exists in vera-bot/ folder
2. Contains: `ANTHROPIC_API_KEY=sk-ant-xxxxx`
3. You called `load_dotenv()` at top of main.py

### "No module named 'anthropic'"
→ Run: `pip install anthropic`

### "No contexts_loaded in response"
→ Change from:
```python
"contexts_loaded": {
    "category": len(contexts["category"]),
    ...
}
```
To:
```python
"contexts_loaded": {
    "category": len(contexts.get("category", {})),
    ...
}
```

### Message says "Hi there, we have an opportunity"
→ Claude isn't being called. Check:
1. API key is valid (test: `python -c "import anthropic; print(anthropic.Anthropic())"`)
2. `compose_message()` function is being called in `/v1/tick`
3. No try-except is silently catching the error

### "403 Unauthorized" from Claude API
→ API key is wrong or expired. Get a new one from console.anthropic.com

---

## What Your Final Submission Should Look Like

```
vera-bot/
├── main.py (your bot code)
├── .env (API key - don't commit to GitHub)
├── README.md (what you built)
├── requirements.txt (pip packages)
└── (no expanded/ folder - judge provides data)
```

**GitHub (public):**
- Everything except `.env`
- Include `requirements.txt`

**Render:**
- Connected to GitHub repo
- Environment variable: ANTHROPIC_API_KEY=xxx
- Start command: `uvicorn main:app --host 0.0.0.0 --port 8000`
- Public URL: https://vera-bot-xyz.onrender.com

---

## Submission Form (May 3, 11 PM)

```
Full name: [Your actual name]
Email: [Your email]
Phone: [Your phone]
Submission URL: https://vera-bot-xyz.onrender.com  ← EXACTLY THIS FORMAT
LinkedIn: [optional]
```

**Keep your bot URL LIVE for 3+ days after submission.** The judge will call it automatically.

---

## Last-Minute Checklist (May 3, 10 PM)

- [ ] Bot runs without errors locally
- [ ] `curl http://localhost:8000/v1/healthz` returns 200
- [ ] Messages contain specific numbers/offers (not generic)
- [ ] Judge simulator shows 7+/10 scores
- [ ] Public URL on Render is live
- [ ] Team name in metadata is correct
- [ ] `.env` file is NOT in GitHub
- [ ] `requirements.txt` includes all packages
- [ ] README.md is written

**If ALL checkboxes are ✓:**
→ You're ready to submit!

Go to: https://partners.magicpin.in/vera/ai-challenge
Fill form. Submit. Done! 🎉

---

## QUICK DOS & DON'TS

✅ DO:
- Use data from `contexts[scope][id]`
- Include 1-2 specific facts per message
- Have one clear yes/no CTA
- Test locally before deploying
- Deploy on Render (or similar)
- Keep bot live after submission

❌ DON'T:
- Invent numbers (hallucinate)
- Send generic copy
- Multiple CTAs per message
- Forget to set API key on Render
- Close your bot after submitting
- Miss the May 3, 11 PM deadline

---

## YOU'VE GOT THIS! 

Start with: `python main.py` 

Iterate with: `curl http://localhost:8000/v1/tick ...`

Deploy with: Render.com

Submit with: The form on the challenge page

Questions? Re-read the brief. Errors? Google them. Stuck? Ask me! 💪
