# QUICK START CODE TEMPLATE
# Copy this into main.py and modify the marked sections

from fastapi import FastAPI
from typing import Optional, List, Dict, Any
import json
import os
from datetime import datetime
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ADJUST THIS PATH to where your expanded/ folder is
EXPANDED_DIR = "../magicpin-challenge/expanded"

# In-memory storage
contexts = {"category": {}, "merchant": {}, "customer": {}, "trigger": {}}
sent_messages = set()
conversation_history = {}  # Track ongoing conversations

# Load data
try:
    with open(f"{EXPANDED_DIR}/categories.json") as f:
        categories_data = json.load(f)
    with open(f"{EXPANDED_DIR}/merchants.json") as f:
        merchants_data = json.load(f)
    with open(f"{EXPANDED_DIR}/triggers.json") as f:
        triggers_data = json.load(f)
    print("✓ All data loaded successfully")
except Exception as e:
    print(f"⚠ Error loading data: {e}")
    merchants_data = {}
    categories_data = {}
    triggers_data = {}


# ============= ENDPOINTS =============

@app.get("/v1/healthz")
async def health():
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
    return {
        "team_name": "Your Team Name Here",  # ← CHANGE THIS
        "team_members": ["Your Name"],  # ← CHANGE THIS
        "model": "claude-opus-4-20250514",
        "approach": "Signal ranker + grounded composer + reply handler",
        "version": "1.0.0"
    }


@app.post("/v1/context")
async def store_context(data: Dict[str, Any]):
    scope = data.get("scope")
    context_id = data.get("context_id")
    version = data.get("version")
    payload = data.get("payload")
    
    if scope not in contexts:
        contexts[scope] = {}
    
    contexts[scope][context_id] = {
        "version": version,
        "payload": payload
    }
    
    return {
        "accepted": True,
        "ack_id": f"ack_{context_id}_{version}",
        "stored_at": datetime.now().isoformat()
    }


@app.post("/v1/tick")
async def tick(data: Dict[str, Any]):
    """Main endpoint - compose and send messages"""
    available_triggers = data.get("available_triggers", [])
    
    if not available_triggers:
        return {"actions": []}
    
    # Rank signals
    actions = []
    for trigger_id in available_triggers[:5]:  # Process top 5 triggers
        
        # Get merchants in this trigger's category
        trigger_data = triggers_data.get(trigger_id, {})
        trigger_category = trigger_data.get("category")
        
        for merchant_id, merchant in merchants_data.items():
            if merchant.get("category") != trigger_category:
                continue
            
            # Skip if already sent
            supp_key = f"{trigger_id}:{merchant_id}"
            if supp_key in sent_messages:
                continue
            
            # Compose message
            try:
                body = compose_message(merchant_id, trigger_id)
            except Exception as e:
                print(f"Error composing for {merchant_id}: {e}")
                body = f"Hi {merchant.get('name', 'there')}, we have an opportunity for you. Interested?"
            
            action = {
                "merchant_id": merchant_id,
                "trigger_id": trigger_id,
                "body": body,
                "cta": "open_ended",
                "suppression_key": supp_key
            }
            actions.append(action)
            sent_messages.add(supp_key)
            
            if len(actions) >= 20:  # Judge limit
                break
        
        if len(actions) >= 20:
            break
    
    return {"actions": actions}


@app.post("/v1/reply")
async def reply(data: Dict[str, Any]):
    """Handle merchant replies"""
    message = data.get("message", "")
    conv_id = data.get("conversation_id")
    
    # Simple intent classification
    if any(word in message.lower() for word in ["yes", "ok", "sure", "go", "send", "sounds good"]):
        return {
            "action": "send",
            "body": "Perfect! I'm preparing that now. Check your dashboard in a minute.",
            "rationale": "Merchant accepted"
        }
    elif any(word in message.lower() for word in ["no", "not", "don't", "stop", "later", "busy"]):
        return {
            "action": "end",
            "body": "Got it. I'll check in another time.",
            "rationale": "Merchant declined"
        }
    else:
        return {
            "action": "send",
            "body": "Glad you're interested! The data shows local demand for your services. Should we run a campaign?",
            "rationale": "Merchant has questions or is unclear"
        }


# ============= HELPER FUNCTIONS =============

def compose_message(merchant_id: str, trigger_id: str) -> str:
    """Use Claude to compose a specific, grounded message"""
    
    # Get merchant and trigger data
    merchant = merchants_data.get(merchant_id, {})
    trigger = triggers_data.get(trigger_id, {})
    category = merchant.get("category", "unknown")
    
    # Build context
    merchant_info = f"""
Merchant: {merchant.get('name', merchant_id)}
Category: {category}
Performance: {merchant.get('performance_metrics', {})}
Recent offers: {merchant.get('offers', [])}
"""
    
    trigger_info = f"""
Trigger type: {trigger.get('type')}  
Local data: {trigger.get('local_data', {})}
Description: {trigger.get('description')}
"""
    
    category_info = f"""
Tone: professional and specific
Pattern: Include a number, benchmark, or specific offer
Length: 1-2 sentences max
"""
    
    # Create system prompt
    system = f"""You are Vera, composing a message for a merchant.

RULES:
- Use ONLY facts from context. Never invent numbers.
- Include ONE specific detail (number, offer, or local benchmark).
- ONE clear yes/no question or call-to-action.
- Keep it 1-2 sentences.
- Professional tone.

MERCHANT INFO:
{merchant_info}

TRIGGER INFO:
{trigger_info}

CATEGORY RULES:
{category_info}

Return ONLY the message text. No explanations."""

    try:
        msg = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=100,
            system=system,
            messages=[{
                "role": "user",
                "content": f"Compose message for {merchant_id} based on {trigger_id}"
            }]
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"Compose error: {e}")
        # Fallback to simple template
        return f"Hi {merchant.get('name')}, we see {trigger.get('description')}. Worth exploring?"


if __name__ == "__main__":
    import uvicorn
    print("Starting Vera bot...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
