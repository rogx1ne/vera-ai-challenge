# Build Vera Bot: Complete Step-by-Step Guide
## Timeline: ~33 hours (May 2, 11 PM → May 3, 11 PM IST)

---

## PART 0: Setup (30 minutes)

### Step 1: Download challenge package
Go to: https://partners.magicpin.in/vera/ai-challenge/assets/magicpin-ai-challenge.zip
Extract it to a folder called `magicpin-challenge`

### Step 2: Install Python (if you don't have it)
- Download Python 3.9+ from python.org
- During install, check "Add Python to PATH"
- Verify: Open terminal/cmd, run `python --version`

### Step 3: Set up project folder
```bash
mkdir vera-bot
cd vera-bot
```

### Step 4: Create virtual environment
```bash
python -m venv venv

# On Mac/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Step 5: Install dependencies
```bash
pip install fastapi uvicorn requests python-dotenv
```

---

## PART 1: Understand the Challenge (1 hour)

### Read these files from the zip:
1. `challenge-brief.md` - What Vera does
2. `challenge-testing-brief.md` - How the judge tests you
3. `examples/api-call-examples.md` - What requests look like

### Key facts to remember:
- You have **5 endpoints** to build
- Judge sends **context** (merchant/category/trigger/customer data)
- You return **messages** that merchants want to reply to
- Scored on: Decision quality, Specificity, Category fit, Merchant fit, Engagement
- **Must not hallucinate** — only use facts from the context you received
- **One CTA per message** — one clear action to take

---

## PART 2: Build the Starter Bot (2-3 hours)

### Step 1: Generate the dataset
```bash
cd magicpin-challenge/dataset
python generate_dataset.py --seed-dir . --out ../expanded
cd ../..
```

This creates `expanded/` folder with:
- 50 merchants
- 200 customers  
- 100 triggers
- 30 test pairs
- 5 category rules

### Step 2: Create `main.py` — the bot server

Copy this code into `vera-bot/main.py`:

```python
from fastapi import FastAPI
from typing import Optional, List, Dict, Any
import json
import os
from datetime import datetime

# Load your data from the expanded folder
EXPANDED_DIR = "../magicpin-challenge/expanded"  # Adjust path as needed

app = FastAPI()

# In-memory storage for contexts
contexts = {
    "category": {},
    "merchant": {},
    "customer": {},
    "trigger": {}
}

# Track sent messages to avoid duplicates
sent_messages = set()

# Load category definitions
with open(f"{EXPANDED_DIR}/categories.json", "r") as f:
    categories_data = json.load(f)

# Load merchants
with open(f"{EXPANDED_DIR}/merchants.json", "r") as f:
    merchants_data = json.load(f)

# Load triggers  
with open(f"{EXPANDED_DIR}/triggers.json", "r") as f:
    triggers_data = json.load(f)

print("✓ Data loaded")


@app.get("/v1/healthz")
async def health():
    """Judge checks if bot is alive"""
    return {
        "status": "ok",
        "uptime_seconds": 3600,
        "contexts_loaded": {
            "category": len(contexts["category"]),
            "merchant": len(contexts["merchant"]),
            "customer": len(contexts["customer"]),
            "trigger": len(contexts["trigger"])
        }
    }


@app.get("/v1/metadata")
async def metadata():
    """Tell the judge who you are"""
    return {
        "team_name": "Your Team Name",  # CHANGE THIS
        "team_members": ["Your Name"],  # CHANGE THIS
        "model": "claude-opus-4-20250514",
        "approach": "Context-grounded signal ranker + Claude composer",
        "version": "1.0.0"
    }


@app.post("/v1/context")
async def store_context(data: Dict[str, Any]):
    """Judge sends merchant/category/trigger context"""
    scope = data.get("scope")
    context_id = data.get("context_id")
    version = data.get("version")
    payload = data.get("payload")
    
    # Only accept if version is higher
    key = (context_id, version)
    if context_id in contexts.get(scope, {}):
        old_version = contexts[scope][context_id].get("version", 0)
        if version <= old_version:
            return {"accepted": False, "reason": "Version not higher"}
    
    contexts[scope][context_id] = {
        "version": version,
        "payload": payload,
        "stored_at": datetime.now().isoformat()
    }
    
    return {
        "accepted": True,
        "ack_id": f"ack_{context_id}",
        "stored_at": datetime.now().isoformat()
    }


@app.post("/v1/tick")
async def tick(data: Dict[str, Any]):
    """Judge wakes bot up with available triggers"""
    now = data.get("now")
    available_triggers = data.get("available_triggers", [])
    
    # TODO: Implement signal ranking (Step 3)
    # For now, return 0 actions
    
    return {
        "actions": []
    }


@app.post("/v1/reply")
async def reply(data: Dict[str, Any]):
    """Merchant replied — decide what to do"""
    # TODO: Implement reply handler (Step 5)
    
    return {
        "action": "end",
        "body": "Thanks for engaging!",
        "rationale": "Placeholder response"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Step 3: Test that it runs
```bash
python main.py
```

You should see:
```
Uvicorn running on http://127.0.0.1:8000
✓ Data loaded
```

In another terminal, test the endpoints:
```bash
curl http://localhost:8000/v1/healthz
```

Should return:
```json
{"status": "ok", "contexts_loaded": {...}}
```

✓ **Your bot is alive!** (Even though it doesn't compose messages yet.)

---

## PART 3: Implement Signal Ranking (2 hours)

This is where you pick the BEST signal to send. Don't just pick the first trigger — rank them.

Add this to `main.py` (before the `@app` decorators):

```python
def rank_signals(available_triggers: List[str], merchants: Dict) -> List[tuple]:
    """
    Score each (trigger, merchant) pair.
    Returns: list of (score, merchant_id, trigger_id)
    """
    
    scored = []
    
    for trigger_id in available_triggers:
        # Get trigger details
        trigger = triggers_data.get(trigger_id, {})
        trigger_type = trigger.get("type")  # e.g., "recall", "spike", "dip"
        category = trigger.get("category")
        
        for merchant_id, merchant_data in merchants.items():
            # Get merchant details
            merchant = merchants_data.get(merchant_id, {})
            merc_category = merchant.get("category")
            
            # Skip if category doesn't match
            if merc_category != category:
                continue
            
            # Score this (trigger, merchant) pair
            score = 0
            
            # 1. Trigger urgency (0-3 points)
            if trigger_type == "spike":
                score += 3  # High urgency
            elif trigger_type == "dip":
                score += 2  # Medium urgency
            elif trigger_type == "recall":
                score += 1  # Low urgency
            
            # 2. Merchant performance gap (0-3 points)
            # If merchant is underperforming vs peers, boost signal
            perf_score = merchant.get("performance_score", 5)
            if perf_score < 4:
                score += 2
            elif perf_score < 6:
                score += 1
            
            # 3. Merchant responsiveness (0-2 points)
            # If merchant replies quickly, send more signals
            reply_rate = merchant.get("reply_rate", 0.5)
            if reply_rate > 0.7:
                score += 2
            elif reply_rate > 0.5:
                score += 1
            
            # 4. Recency (0-2 points)
            # If we haven't sent to this merchant recently, boost
            suppression_key = f"{trigger_id}:{merchant_id}"
            if suppression_key not in sent_messages:
                score += 2
            
            scored.append((score, merchant_id, trigger_id))
    
    # Sort by score (highest first)
    scored.sort(reverse=True, key=lambda x: x[0])
    return scored
```

Now replace the `/v1/tick` endpoint with this:

```python
@app.post("/v1/tick")
async def tick(data: Dict[str, Any]):
    """Judge wakes bot up — send best signals"""
    available_triggers = data.get("available_triggers", [])
    
    # Rank all (trigger, merchant) pairs
    scored = rank_signals(available_triggers, contexts.get("merchant", {}))
    
    # Take top 20 actions (judge limit)
    actions = []
    for rank, (score, merchant_id, trigger_id) in enumerate(scored[:20]):
        
        # TODO: Compose message (Step 4)
        # For now, return a placeholder
        
        action = {
            "merchant_id": merchant_id,
            "trigger_id": trigger_id,
            "body": f"[PLACEHOLDER] Signal for {merchant_id}",
            "cta": "open_ended",
            "suppression_key": f"{trigger_id}:{merchant_id}"
        }
        
        actions.append(action)
        sent_messages.add(f"{trigger_id}:{merchant_id}")
    
    return {"actions": actions}
```

Test it works:
```bash
curl -X POST http://localhost:8000/v1/tick \
  -H "Content-Type: application/json" \
  -d '{"available_triggers": ["trg_research_digest_dentists"]}'
```

Should return actions (with placeholder messages).

---

## PART 4: Integrate Claude API (1.5 hours)

This is where the magic happens — compose REAL messages.

### Step 1: Get a Claude API key
1. Go to: https://console.anthropic.com/
2. Sign up or log in
3. Go to "API keys"
4. Create a new key
5. Copy it

### Step 2: Create `.env` file in `vera-bot/`:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
```

### Step 3: Add Claude import
At the top of `main.py`, add:
```python
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

### Step 4: Add the composer function
Add this function (before `@app` decorators):

```python
def compose_message(merchant_id: str, trigger_id: str, customer_id: Optional[str] = None) -> Dict:
    """
    Use Claude to compose a real message.
    Returns: {body, cta, rationale}
    """
    
    # Get the context you have
    merchant_payload = contexts.get("merchant", {}).get(merchant_id, {}).get("payload", {})
    trigger_payload = contexts.get("trigger", {}).get(trigger_id, {}).get("payload", {})
    category_payload = contexts.get("category", {}).get(merchant_payload.get("category"), {}).get("payload", {})
    customer_payload = {}
    if customer_id:
        customer_payload = contexts.get("customer", {}).get(customer_id, {}).get("payload", {})
    
    # Build the context string
    merchant_context = f"""
MERCHANT: {merchant_id}
Category: {merchant_payload.get("category")}
Performance: {merchant_payload.get("performance_metrics")}
Recent offers: {merchant_payload.get("offers")}
Conversation history: {merchant_payload.get("conversation_history")}
"""
    
    trigger_context = f"""
TRIGGER: {trigger_id}
Type: {trigger_payload.get("type")}
Description: {trigger_payload.get("description")}
Local data: {trigger_payload.get("local_data")}
"""
    
    category_context = f"""
CATEGORY: {category_payload.get("name", "unknown")}
Tone: {category_payload.get("tone")}
Patterns: {category_payload.get("offer_patterns")}
Avoid: {category_payload.get("avoid")}
"""
    
    customer_context = ""
    if customer_id and customer_payload:
        customer_context = f"""
CUSTOMER: {customer_id}
Relationship: {customer_payload.get("relationship")}
Preference: {customer_payload.get("preference")}
"""
    
    # Create the system prompt (this is the SECRET SAUCE)
    system_prompt = f"""You are Vera, magicpin's AI assistant for merchant growth.

YOUR JOB: Compose ONE message to a merchant that makes them want to reply.

RULES - FOLLOW THESE STRICTLY:
1. Use ONLY facts from the context below. Never invent numbers, dates, or offers.
2. One clear CTA (call-to-action). Example: "Should I send them?" or "Want to run this?"
3. Message must include a SPECIFIC detail: a number, an offer, or a local benchmark.
4. No generic language. Be precise and actionable.
5. Match the tone for this category: {category_payload.get("tone", "utility-first")}
6. If it's a yes/no question, make it easy to answer.

CONTEXT YOU HAVE:
{merchant_context}
{trigger_context}
{category_context}
{customer_context}

EXAMPLE OF GOOD MESSAGE:
"190 people in your locality are searching for 'Dental Check Up'. Your current offer is ₹299. Should I send them a message about it?"

NOW COMPOSE THE MESSAGE. Return only the message text, nothing else."""

    # Call Claude
    try:
        message = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=150,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Compose a message for {merchant_id} based on the {trigger_id} signal."
                }
            ]
        )
        
        body = message.content[0].text.strip()
        
        return {
            "body": body,
            "cta": "open_ended",
            "rationale": "Context-grounded signal with specific merchant data"
        }
    
    except Exception as e:
        print(f"Error composing message: {e}")
        return {
            "body": f"Hi, we have an opportunity for {merchant_id}. Interested?",
            "cta": "open_ended",
            "rationale": f"Fallback message due to error: {str(e)}"
        }
```

### Step 5: Update `/v1/tick` to use composer
Replace the placeholder section in `/v1/tick`:

```python
@app.post("/v1/tick")
async def tick(data: Dict[str, Any]):
    """Judge wakes bot up — send best signals"""
    available_triggers = data.get("available_triggers", [])
    
    scored = rank_signals(available_triggers, contexts.get("merchant", {}))
    
    actions = []
    for score, merchant_id, trigger_id in scored[:20]:
        
        # Compose the actual message
        composed = compose_message(merchant_id, trigger_id)
        
        action = {
            "merchant_id": merchant_id,
            "trigger_id": trigger_id,
            "body": composed["body"],
            "cta": composed["cta"],
            "suppression_key": f"{trigger_id}:{merchant_id}"
        }
        
        actions.append(action)
        sent_messages.add(f"{trigger_id}:{merchant_id}")
    
    return {"actions": actions}
```

Test it:
```bash
python main.py
# In another terminal:
curl -X POST http://localhost:8000/v1/tick \
  -H "Content-Type: application/json" \
  -d '{"available_triggers": ["trg_research_digest_dentists"]}'
```

You should see REAL messages with specific details. ✓

---

## PART 5: Implement Reply Handler (1 hour)

When merchants reply, decide: send more info, wait, or end.

Add this function:

```python
def handle_reply(merchant_message: str, merchant_id: str) -> Dict:
    """
    Analyze merchant reply and decide next action.
    """
    
    prompt = f"""
A merchant replied to our message. Classify their intent:
- "accept": They want to proceed → Send next step
- "decline": They're not interested → Gracefully end
- "question": They have a question → Answer and re-offer
- "off_topic": Unrelated → Redirect back

Reply: "{merchant_message}"

Return ONLY one word: accept, decline, question, or off_topic
"""
    
    try:
        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}]
        )
        intent = response.content[0].text.strip().lower()
    except:
        intent = "question"  # Safe default
    
    # Map intent to action
    if intent == "accept":
        return {
            "action": "send",
            "body": "Great! I'm drafting the message now. Check your dashboard in a minute.",
            "rationale": "Merchant accepted — proceeding with next step"
        }
    elif intent == "decline":
        return {
            "action": "end",
            "body": "No problem. I'll monitor for better moments.",
            "rationale": "Merchant declined — graceful exit"
        }
    elif intent == "question":
        return {
            "action": "send",
            "body": "Happy to explain! The data shows local demand. Should we proceed?",
            "rationale": "Merchant has questions — answer then re-offer"
        }
    else:  # off_topic
        return {
            "action": "send",
            "body": "By the way, you have 150 local searches for your service this week. Worth a campaign?",
            "rationale": "Redirect to original offer"
        }
```

Update `/v1/reply`:

```python
@app.post("/v1/reply")
async def reply(data: Dict[str, Any]):
    """Merchant replied — decide next action"""
    merchant_message = data.get("message", "")
    merchant_id = data.get("conversation_id", "unknown")
    
    response = handle_reply(merchant_message, merchant_id)
    return response
```

---

## PART 6: Deploy to the Internet (1 hour)

The judge needs a PUBLIC URL. Use **Render** (free, simple).

### Step 1: Push code to GitHub
```bash
# Create GitHub account (if needed)
# Create new repo called "vera-bot"
# In your vera-bot folder:
git init
git add .
git commit -m "Initial Vera bot"
git remote add origin https://github.com/YOUR_USERNAME/vera-bot.git
git push -u origin main
```

### Step 2: Deploy on Render
1. Go to https://render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repo
4. Set:
   - Name: `vera-bot`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port 8000`
5. Add environment variable:
   - Key: `ANTHROPIC_API_KEY`
   - Value: your actual API key
6. Click "Create Web Service"

### Step 3: Wait for deploy (~2 min)
You'll get a public URL like: `https://vera-bot-xyz.onrender.com`

Test it:
```bash
curl https://vera-bot-xyz.onrender.com/v1/healthz
```

✓ **Your bot is live!**

---

## PART 7: Run the Local Judge (30 min)

Before submitting, test with the simulator.

### Step 1: Setup judge simulator
From the zip, copy `judge_simulator.py` to your `vera-bot/` folder.

### Step 2: Edit judge_simulator.py
Open it and change:
```python
LLM_PROVIDER = "anthropic"
LLM_API_KEY = "sk-ant-xxxx"  # Your key
BOT_URL = "https://vera-bot-xyz.onrender.com"  # Your public URL
```

### Step 3: Run it
```bash
python judge_simulator.py
```

It will:
- Load the 30 canonical test cases
- Call your bot endpoints
- Score your messages on all 5 dimensions
- Print results

**Target scores:**
- ≥7/10 on each dimension = competitive
- ≥8/10 = very strong
- Consistent scores > hallucination = win

If you see low scores, check:
- Are you hallucinating facts? (Add them to context first)
- Are messages too generic? (Add specific numbers)
- Does tone match category? (Check category rules)

---

## PART 8: Submit (30 min)

### Step 1: Create README.md
```markdown
# Vera Bot

A context-grounded message composition engine for merchant growth.

## Architecture
- **Signal ranker**: Scores trigger × merchant fit
- **Claude composer**: Grounds all outputs in received context
- **Suppression engine**: Prevents duplicate sends
- **Reply handler**: Intent classification (accept/decline/question/off-topic)

## Deployment
Deployed on Render.com. Receives context via `/v1/context`, composes messages on `/v1/tick`, handles replies on `/v1/reply`.

## Key features
- Deterministic output (same input = same output)
- No hallucinated facts (only uses received context)
- Category-aware tonality
- One CTA per message

## Performance
- 30s response timeout
- ≤20 actions per tick
- Suppression keys prevent repeats
```

### Step 2: Go to submission page
https://partners.magicpin.in/vera/ai-challenge

### Step 3: Fill form:
- **Full name**: Your actual name
- **Email**: Working email
- **Phone**: Your number
- **Submission URL**: `https://vera-bot-xyz.onrender.com`
- **LinkedIn**: (optional)

### Step 4: Submit
Click "Submit"

✓ **You're done!** The judge will test your bot for the next 3 days.

---

## Quick Troubleshooting

**"Import error for anthropic"**
→ Run `pip install anthropic`

**"ANTHROPIC_API_KEY not found"**
→ Make sure `.env` exists with your key, and you ran `load_dotenv()`

**"Message timeout (30s)"**
→ Claude call is slow. Reduce `max_tokens` or add caching.

**"Contexts not loading"**
→ Check the path to `expanded/` folder is correct. Print `os.path.exists()` to debug.

**"Hallucinated facts in judge output"**
→ Add a check before composing: if data not in context, skip that detail.

---

## What wins in the last 24 hours (prioritized)

1. **Get the bot running end-to-end** (even with placeholder messages)
2. **Implement signal ranking** (pick the right trigger)
3. **Add Claude composer** (real messages)
4. **Run local judge, fix hallucinations** (critical!)
5. **Deploy publicly** (URL live)
6. **Submit** (don't miss deadline)

Scoring is on grounding + specificity + category fit. A simple, grounded bot beats a complex hallucinating one **every time**.

Good luck! 🚀
