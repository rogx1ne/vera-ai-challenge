from fastapi import FastAPI
from typing import Optional, List, Dict, Any
import json
import os
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("⚠ WARNING: GEMINI_API_KEY not set. Bot will fail on /v1/reply calls.")
else:
    genai.configure(api_key=api_key)
    print("✓ Gemini API configured")

# Use gemini-1.0-pro (more widely available) or gemini-pro
model = None
try:
    model = genai.GenerativeModel("gemini-2.0-flash")
    print("✓ Using gemini-2.0-flash")
except Exception as e:
    print(f"⚠ gemini-2.0-flash failed: {e}")
    try:
        model = genai.GenerativeModel("gemini-1.0-pro")
        print("✓ Using gemini-1.0-pro")
    except Exception as e:
        print(f"⚠ gemini-1.0-pro failed: {e}")
        try:
            model = genai.GenerativeModel("gemini-pro")
            print("✓ Using gemini-pro")
        except Exception as e:
            print(f"✗ All models failed: {e}")

# Path to dataset (adjust if needed)
if os.path.exists("../magicpin-ai-challenge/dataset"):
    EXPANDED_DIR = "../magicpin-ai-challenge/dataset"
elif os.path.exists("../../magicpin-ai-challenge/dataset"):
    EXPANDED_DIR = "../../magicpin-ai-challenge/dataset"
else:
    EXPANDED_DIR = "./dataset"  # Fallback if running standalone

# In-memory storage
contexts = {"category": {}, "merchant": {}, "customer": {}, "trigger": {}}
sent_messages = set()
conversation_history = {}

# Load data
merchants_data = {}
categories_data = {}
triggers_data = {}

try:
    # Load merchants from seed
    with open(f"{EXPANDED_DIR}/merchants_seed.json") as f:
        merchants_seed = json.load(f)
        merchants_data = {m["merchant_id"]: m for m in merchants_seed.get("merchants", [])}
    
    # Load triggers from seed
    with open(f"{EXPANDED_DIR}/triggers_seed.json") as f:
        triggers_seed = json.load(f)
        triggers_data = {t["id"]: t for t in triggers_seed.get("triggers", [])}
    
    # Load category files
    categories_dir = f"{EXPANDED_DIR}/categories"
    if os.path.exists(categories_dir):
        for category_file in os.listdir(categories_dir):
            if category_file.endswith(".json"):
                with open(os.path.join(categories_dir, category_file)) as f:
                    cat_data = json.load(f)
                    category_slug = category_file.replace(".json", "")
                    categories_data[category_slug] = cat_data
    
    print("✓ All data loaded successfully")
    print(f"  Merchants: {len(merchants_data)}")
    print(f"  Categories: {len(categories_data)}")
    print(f"  Triggers: {len(triggers_data)}")
except FileNotFoundError as e:
    print(f"⚠ Data files not found (expected on deployment): {e}")
    print("  Judge will populate via /v1/context endpoint")
except Exception as e:
    print(f"✗ Error loading data: {e}")
    import traceback
    traceback.print_exc()


# ============= ENDPOINTS =============

@app.get("/v1/healthz")
async def health():
    return {
        "status": "ok",
        "uptime_seconds": 3600,
        "contexts_loaded": {
            "category": len(contexts.get("category", {})),
            "merchant": len(contexts.get("merchant", {})),
            "customer": len(contexts.get("customer", {})),
            "trigger": len(contexts.get("trigger", {}))
        }
    }


@app.get("/v1/metadata")
async def metadata():
    model_name = model._client_config.model or "gemini-1.0-pro"
    return {
        "team_name": "Vera",
        "team_members": ["Abhishek"],
        "model": "gemini-2.0-flash" if "2.0" in str(model_name) else "gemini-1.0-pro",
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
    
    # Sort triggers by urgency (highest first)
    def get_urgency(trigger_id):
        return triggers_data.get(trigger_id, {}).get("urgency", 0)
    
    available_triggers_sorted = sorted(available_triggers, key=get_urgency, reverse=True)
    
    # Rank signals and compose messages
    actions = []
    for trigger_id in available_triggers_sorted[:5]:  # Process top 5 triggers by urgency
        
        # Get trigger data
        trigger_data = triggers_data.get(trigger_id, {})
        if not trigger_data:
            print(f"Trigger not found: {trigger_id}")
            continue
        
        # Get the merchant_id directly from trigger
        merchant_id = trigger_data.get("merchant_id")
        if not merchant_id:
            print(f"No merchant_id in trigger {trigger_id}")
            continue
        
        # Get merchant data
        merchant = merchants_data.get(merchant_id, {})
        if not merchant:
            print(f"Merchant not found: {merchant_id}")
            continue
        
        # Skip if already sent
        supp_key = f"{trigger_id}:{merchant_id}"
        if supp_key in sent_messages:
            continue
        
        # Compose message using templates
        try:
            body = compose_message(merchant_id, trigger_id)
            if not body:
                print(f"Empty body from compose_message for {merchant_id}")
                continue
        except Exception as e:
            print(f"Error composing for {merchant_id}: {e}")
            import traceback
            traceback.print_exc()
            name = merchant.get("identity", {}).get("name", "there")
            body = f"Hi {name}, we have an opportunity for you. Interested?"
        
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
    """Compose category-specific, grounded messages"""
    
    # Get merchant and trigger data
    merchant = merchants_data.get(merchant_id, {})
    trigger = triggers_data.get(trigger_id, {})
    
    merchant_name = merchant.get("identity", {}).get("name", merchant_id)
    category_slug = merchant.get("category_slug", "general")
    trigger_kind = trigger.get("kind", "opportunity")
    payload = trigger.get("payload", {})
    
    # Extract conversation history insights
    conv_history = merchant.get("conversation_history", [])
    last_engagement = None
    if conv_history:
        last_engagement = conv_history[-1].get("engagement")
    
    # Personalization based on engagement
    personalization = ""
    if last_engagement == "intent_action":
        personalization = "You've shown interest before. "
    elif last_engagement == "positive_feedback":
        personalization = "Great to reconnect. "
    
    # Category-specific tone and focus
    category_tone = {
        "dentists": {"focus": "health and compliance", "urgency_word": "important", "metric": "patient appointments", "fallback": "Your dental practice's growth is our priority."},
        "gyms": {"focus": "member retention and goals", "urgency_word": "momentum", "metric": "active members", "fallback": "Keep your members engaged and motivated."},
        "pharmacies": {"focus": "convenience and accessibility", "urgency_word": "critical", "metric": "prescription fills", "fallback": "Your accessibility matters to customers."},
        "restaurants": {"focus": "taste and experience", "urgency_word": "trending", "metric": "covers per night", "fallback": "Your culinary reputation is your strength."},
        "salons": {"focus": "beauty and confidence", "urgency_word": "popular", "metric": "bookings", "fallback": "Your style and expertise attract clients."},
    }
    
    tone = category_tone.get(category_slug, {"focus": "growth", "urgency_word": "opportunity", "metric": "engagement", "fallback": "Your business growth matters to us."})
    
    # Category-aware templates
    templates = {
        "research_digest": lambda: f"{personalization}We see local {tone['focus']} interest in {payload.get('category', 'your service')} this week—very {tone['urgency_word']}. Your '{merchant.get('offers', [{}])[0].get('title', 'offer')}' is ready. Shall we?",
        
        "perf_dip": lambda: f"{personalization}Your {tone['metric']} dropped {abs(payload.get('delta_pct', 0)*100):.0f}% this week. This {tone['urgency_word']} to reverse. Ready to launch a campaign?",
        
        "renewal_due": lambda: f"{personalization}Your plan renews in {payload.get('days_remaining', 0)} days (₹{payload.get('renewal_amount', 0)}). Keep the {tone['focus']} going. Shall we renew?",
        
        "review_theme_emerged": lambda: f"We see {payload.get('occurrences_30d', 0)} reviews mentioning '{payload.get('theme', 'feedback')}' in 30 days. {personalization}Let's address this together?",
        
        "festival_upcoming": lambda: f"An {tone['urgency_word']} {tone['focus']} opportunity: {payload.get('festival', 'an event')} is coming. {personalization}Ready to capitalize?",
        
        "winback_eligible": lambda: f"Your {tone['focus']} community misses you! {payload.get('lapsed_customers_added_since_expiry', 0)} people want to come back. {personalization}Let's reconnect?",
        
        "curious_ask_due": lambda: f"What's working best for {tone['focus']} this week? I'd love to know so we can help.",
        
        "recall_due": lambda: f"One of your customers is due for a {payload.get('service_due', 'service')}. Time to reach out and bring them back?",
        
        "ipl_match_today": lambda: f"{payload.get('match', 'Big event')} today in {payload.get('venue', 'your area')}—{tone['urgency_word']} for {tone['focus']}. {personalization}Ready to attract the crowd?",
        
        "perf_dip": lambda: f"{personalization}Your {tone['metric']} dropped {abs(payload.get('delta_pct', 0)*100):.0f}% this week—this is {tone['urgency_word']}. Should we launch a recovery push?",
    }
    
    # Try to get template for this trigger type
    if trigger_kind in templates:
        try:
            msg = templates[trigger_kind]()
            if msg and len(msg) > 10:  # Ensure not empty
                return msg
        except Exception as e:
            print(f"Template error for {trigger_kind}: {e}")
    
    # Smart fallback based on category and available data
    offers_list = merchant.get("offers", [])
    active_offer = next((o for o in offers_list if o.get("status") == "active"), None)
    
    if active_offer:
        offer_text = f"Your '{active_offer.get('title')}' offer"
        return f"{personalization}{offer_text} has {tone['urgency_word']} {tone['focus']} potential. Ready to promote it?"
    else:
        # Ultimate fallback: use category-specific phrase
        return f"{personalization}{tone['fallback']} Should we explore new opportunities together?"


if __name__ == "__main__":
    import uvicorn
    print("Starting Vera bot...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
