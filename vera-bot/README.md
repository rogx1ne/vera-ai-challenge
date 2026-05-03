# Vera Bot - AI Merchant Communication Engine

A FastAPI-based bot that intelligently composes and responds to merchant messages using **trigger ranking**, **conversation history personalization**, and **category-specific messaging**.

**Status:** ✅ Deployed to Render | **Model:** GPT-3.5-turbo | **Python:** 3.14 | **Framework:** FastAPI

---

## 🎯 Architecture

```
User Query
    ↓
[/v1/tick] - Rank triggers by urgency
    ↓
[Compose Message] - Category-specific tone + personalization
    ↓
Return Action (merchant_id, trigger_id, message, CTA)
    ↓
[/v1/reply] - Weighted intent scoring (Accept/Decline/Clarify)
    ↓
Return Response + Confidence + Reason Code
```

---

## ✨ Key Improvements (Latest)

### 1. **Enhanced Reply Handler** (NEW)
- **Weighted intent scoring** with 10+ keyword signals
- **Reason codes**: `explicit_accept`, `explicit_decline`, `unclear_intent`
- **Confidence scoring** (0-1 scale, 0.95 for high-confidence decisions)
- **Multi-signal detection**: Accumulates score from multiple words
- **Smart fallback**: Asks clarifying questions when unclear

**Example:**
```
Input: "Yes, absolutely! Let's do it."
Output: {
  "action": "send",
  "reason_code": "explicit_accept",
  "confidence": 0.95,
  "body": "Excellent! I'm setting this up now..."
}
```

### 2. **Category Expansion** (NEW)
Supports **12 merchant categories** (up from 5):

| Original | New Categories |
|----------|-----------------|
| Dentists | Beauty Spas |
| Gyms | Fitness |
| Pharmacies | Healthcare |
| Restaurants | Food Delivery |
| Salons | Fashion, Education, Automotive |

Each category has **unique tone, vocabulary, and metrics**:
- **Dentists**: "health and compliance" | metric: "patient appointments"
- **Restaurants**: "taste and experience" | metric: "covers per night"
- **Fitness**: "fitness goals and transformation" | metric: "active members"
- **Healthcare**: "patient wellbeing" | metric: "patient visits"

### 3. **Robust Error Handling** (NEW)
- Graceful fallbacks for missing data
- Type-safe attribute access (prevents crashes on malformed payload)
- Last-resort fallback messages
- Comprehensive try-catch wrapper on message composition

### 4. **Trigger Ranking by Urgency** (Existing)
Processes triggers in order: Urgency 4 → 3 → 2 → 1

### 5. **Merchant Conversation History** (Existing)
Adds personalization: "You've shown interest before." when detected

---

## 📋 Endpoints

### GET `/v1/healthz`
Health check with context count.
```bash
curl http://localhost:8000/v1/healthz
```
Response:
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

### GET `/v1/metadata`
Bot configuration.
```bash
curl http://localhost:8000/v1/metadata
```
Response:
```json
{
  "team_name": "Vera",
  "team_members": ["Abhishek"],
  "model": "gpt-3.5-turbo",
  "approach": "Signal ranker + grounded composer + reply handler",
  "version": "1.0.0"
}
```

### POST `/v1/context`
Store merchant/category/trigger data.
```bash
curl -X POST http://localhost:8000/v1/context \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "merchant",
    "context_id": "m_001",
    "version": "1.0",
    "payload": {
      "merchant_id": "m_001",
      "category_slug": "restaurants",
      "name": "Test Restaurant"
    }
  }'
```

### POST `/v1/tick`
Process available triggers and generate actions.
```bash
curl -X POST http://localhost:8000/v1/tick \
  -H "Content-Type: application/json" \
  -d '{"available_triggers": ["trg_001", "trg_002"]}'
```
Response:
```json
{
  "actions": [
    {
      "merchant_id": "m_001",
      "trigger_id": "trg_001",
      "body": "We see local research interest in dentists...",
      "cta": "open_ended",
      "suppression_key": "trg_001:m_001"
    }
  ]
}
```

### POST `/v1/reply`
Handle merchant response with intent classification.
```bash
curl -X POST http://localhost:8000/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "Yes!", "conversation_id": "conv_001"}'
```
Response:
```json
{
  "action": "send",
  "body": "Excellent! I'm setting this up now...",
  "rationale": "High intent signal detected",
  "confidence": 0.95,
  "reason_code": "explicit_accept"
}
```

---

## 🚀 Quick Start

### Local Development
```bash
# Clone repo
git clone https://github.com/rogx1ne/vera-ai-challenge
cd vera-ai-challenge/vera-bot

# Create venv
python -m venv venv
source venv/bin/activate

# Install deps
pip install -r requirements.txt

# Set API key
echo "OPENAI_API_KEY=sk_test_..." > .env

# Run bot
python main.py

# In another terminal, test:
curl http://localhost:8000/v1/healthz
```

### Deploy to Render
1. Push to GitHub
2. Create Render service from repo
3. Set environment variable: `OPENAI_API_KEY`
4. Deploy!

Bot will be live at: `https://vera-bot-xxxxx.onrender.com`

---

## 🧪 Testing

### Automated Tests (Pytest)
```bash
pytest test_improvements.py -v
```
Runs 40+ test cases covering:
- Reply handler intent detection
- Category expansion
- Error handling
- Message quality
- Integration tests

### Manual Tests (curl)
See [TESTING.md](../TESTING.md) for comprehensive manual test guide with expected outputs.

---

## 📊 Intent Scoring System

The bot uses **weighted keyword scoring** to classify merchant responses:

```
Positive Signals (3 pts): "yes", "yeah", "absolutely", "definitely", "let's do it"
Positive Signals (2 pts): "ok", "sure", "go", "great", "interested"
Negative Signals (3 pts): "no", "nope", "stop", "not interested", "don't"
Negative Signals (2 pts): "not", "don't", "can't", "skip"
Negative Signals (1 pt):  "later", "busy", "maybe"

Decision:
- positive_score > negative_score → ACCEPT (confidence: 0.5 + score*0.15, max 0.95)
- negative_score > positive_score → DECLINE (confidence: 0.5 + score*0.15, max 0.95)
- Tie/No signals → CLARIFY (confidence: 0.4)
```

---

## 🔧 Configuration

### Environment Variables
- `OPENAI_API_KEY` (required) - OpenAI API key for GPT-3.5-turbo
- `PORT` (optional, default 8000) - Server port

### Requirements
- Python 3.12+
- FastAPI 0.109.0
- Uvicorn 0.27.0
- OpenAI 1.13.0+
- python-dotenv 1.0.0

---

## 📁 Project Structure
```
vera-ai-challenge/
├── vera-bot/
│   ├── main.py                    # Core bot logic (380 lines)
│   ├── requirements.txt           # Python dependencies
│   ├── test_improvements.py       # 40+ pytest cases
│   └── README.md                  # This file
├── dataset/
│   ├── merchants_seed.json        # 10 test merchants
│   ├── triggers_seed.json         # 25 test triggers
│   └── categories/                # Category definitions
├── TESTING.md                      # Manual testing guide
├── runtime.txt                     # Python version (3.12.3)
└── .gitignore                      # Secrets & build files

```

---

## 🎓 Key Features Explained

### Trigger Ranking
```python
# Sorts triggers by urgency (1-4 scale)
sorted_triggers = sorted(triggers, key=lambda t: t.get('urgency', 0), reverse=True)
```
Higher urgency triggers are processed first, ensuring critical messages aren't missed.

### Category-Specific Tone
```python
category_tone = {
    "dentists": {
        "focus": "health and compliance",
        "urgency_word": "important",
        "metric": "patient appointments"
    },
    "restaurants": {
        "focus": "taste and experience",
        "urgency_word": "trending",
        "metric": "covers per night"
    }
}
```
Each category uses domain-specific vocabulary for better relevance.

### Personalization
```python
if last_engagement == "intent_action":
    personalization = "You've shown interest before. "
elif last_engagement == "positive_feedback":
    personalization = "Great to reconnect. "
```
References past interactions to build rapport.

---

## 🐛 Error Handling

Bot gracefully handles:
- Missing merchant data → Falls back to category-specific message
- Malformed triggers → Uses last-resort fallback
- Empty offers → Suggests generic opportunity
- Invalid payloads → Catches and logs, returns safe message
- Network errors → OpenAI errors logged, reply endpoint still responds

---

## 📈 Performance

- **Message composition**: <100ms (template-based, no API calls)
- **Reply classification**: <50ms (keyword matching, no ML inference)
- **Tick processing**: ~10ms per trigger (sorting + filtering)

---

## 🤝 Contributing

To improve the bot:
1. Add test cases to `test_improvements.py`
2. Update templates or category tone in `compose_message()`
3. Enhance intent scoring in `/v1/reply`
4. Run tests: `pytest test_improvements.py -v`
5. Push and redeploy

---

## 📝 License

Challenge submission for Vera AI Challenge (MagicPin)

---

## 🔗 Challenge Links

- Challenge: https://magicpin.com/vera/ai-challenge
- Submission: https://partners.magicpin.in/vera/ai-challenge
- GitHub: https://github.com/rogx1ne/vera-ai-challenge

---

## 📞 Support

Questions? Check:
1. [TESTING.md](../TESTING.md) - Manual test guide
2. [requirements.txt](requirements.txt) - Dependencies
3. [main.py](main.py) - Inline code comments
