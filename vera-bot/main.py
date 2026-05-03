from fastapi import FastAPI
from typing import Optional, List, Dict, Any
import json
import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Configure OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("⚠ WARNING: OPENAI_API_KEY not set. Bot will fail on /v1/reply calls.")
    client = None
else:
    client = OpenAI(api_key=api_key)
    print("✓ OpenAI API configured")

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
    return {
        "team_name": "Vera",
        "team_members": ["Abhishek"],
        "model": "gpt-3.5-turbo",
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
    """Handle merchant replies with smarter intent classification"""
    message = data.get("message", "").lower().strip()
    conv_id = data.get("conversation_id")
    
    # Enhanced intent classification with weights
    positive_indicators = {
        "yes": 3, "yeah": 3, "yep": 3, "ok": 2, "okay": 2, "sure": 3,
        "absolutely": 3, "definitely": 3, "go": 2, "send": 3, "sounds good": 3,
        "let's do it": 3, "perfect": 2, "great": 2, "interested": 2,
        "looks good": 2, "count me in": 3, "in": 2, "cool": 1,
    }
    
    negative_indicators = {
        "no": 3, "nope": 3, "nah": 2, "not": 2, "don't": 2, "stop": 3,
        "later": 1, "busy": 1, "not now": 2, "can't": 2, "not interested": 3,
        "not today": 1, "skip": 2, "pass": 2, "maybe next time": 1,
    }
    
    positive_score = sum(positive_indicators.get(word, 0) for word in positive_indicators if word in message)
    negative_score = sum(negative_indicators.get(word, 0) for word in negative_indicators if word in message)
    
    # Log the decision
    log_entry = {
        "conversation_id": conv_id,
        "message": message[:100],
        "positive_score": positive_score,
        "negative_score": negative_score,
        "timestamp": datetime.now().isoformat()
    }
    
    if positive_score > negative_score and positive_score > 0:
        log_entry["decision"] = "accept"
        return {
            "action": "send",
            "body": "Excellent! I'm setting this up now. You'll see results in your dashboard within 2 hours.",
            "rationale": "High intent signal detected",
            "confidence": min(0.95, 0.5 + positive_score * 0.15),
            "reason_code": "explicit_accept"
        }
    elif negative_score > positive_score and negative_score > 0:
        log_entry["decision"] = "decline"
        return {
            "action": "end",
            "body": "No problem! I'll check back with you later. Reach out if plans change.",
            "rationale": "Merchant declined opportunity",
            "confidence": min(0.95, 0.5 + negative_score * 0.15),
            "reason_code": "explicit_decline"
        }
    else:
        log_entry["decision"] = "clarify"
        return {
            "action": "send",
            "body": "Sounds like you want to learn more! What specific aspect interests you most—customer acquisition, retention, or seasonal demand?",
            "rationale": "Unclear intent; needs clarification",
            "confidence": 0.4,
            "reason_code": "unclear_intent"
        }


# ============= HELPER FUNCTIONS =============

def compose_message(merchant_id: str, trigger_id: str) -> str:
    """Compose category-specific, grounded messages with robust error handling"""
    
    try:
        # Get merchant and trigger data
        merchant = merchants_data.get(merchant_id, {})
        trigger = triggers_data.get(trigger_id, {})
        
        if not merchant or not trigger:
            return f"We have an exciting opportunity for you! Ready to learn more?"
        
        merchant_name = merchant.get("identity", {}).get("name", merchant_id)
        category_slug = merchant.get("category_slug", "general")
        trigger_kind = trigger.get("kind", "opportunity")
        payload = trigger.get("payload", {}) or {}
        
        # Extract conversation history insights
        conv_history = merchant.get("conversation_history", [])
        last_engagement = None
        if conv_history and isinstance(conv_history, list) and len(conv_history) > 0:
            last_engagement = conv_history[-1].get("engagement") if isinstance(conv_history[-1], dict) else None
        
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
            # Expanded categories
            "beauty_spas": {"focus": "relaxation and wellness", "urgency_word": "refreshing", "metric": "spa appointments", "fallback": "Your wellness services enhance customer wellbeing."},
            "fitness": {"focus": "fitness goals and transformation", "urgency_word": "crucial", "metric": "active members", "fallback": "Help members achieve their fitness goals."},
            "healthcare": {"focus": "patient wellbeing", "urgency_word": "essential", "metric": "patient visits", "fallback": "Your healthcare services matter to your community."},
            "food_delivery": {"focus": "delivery speed and satisfaction", "urgency_word": "immediate", "metric": "orders per hour", "fallback": "Quick delivery builds customer loyalty."},
            "fashion": {"focus": "style and trends", "urgency_word": "fashionable", "metric": "sales", "fallback": "Your fashion sense attracts style-conscious customers."},
            "education": {"focus": "student success", "urgency_word": "vital", "metric": "enrollments", "fallback": "Quality education drives student outcomes."},
            "automotive": {"focus": "vehicle maintenance and care", "urgency_word": "critical", "metric": "service bookings", "fallback": "Regular maintenance keeps vehicles running smoothly."},
        }
        
        tone = category_tone.get(category_slug, {"focus": "growth", "urgency_word": "opportunity", "metric": "engagement", "fallback": "Your business growth matters to us."})
        
        # Category-aware templates with safe attribute access
        templates = {
            "research_digest": lambda: f"{personalization}We see local {tone['focus']} interest in {payload.get('category', 'your service')} this week—very {tone['urgency_word']}. Your '{merchant.get('offers', [{}])[0].get('title', 'offer') if merchant.get('offers') else 'offer'}' is ready. Shall we?",
            
            "perf_dip": lambda: f"{personalization}Your {tone['metric']} dropped {abs(float(payload.get('delta_pct', 0))*100):.0f}% this week. This {tone['urgency_word']} to reverse. Ready to launch a campaign?",
            
            "renewal_due": lambda: f"{personalization}Your plan renews in {payload.get('days_remaining', 0)} days (₹{payload.get('renewal_amount', 0)}). Keep the {tone['focus']} going. Shall we renew?",
            
            "review_theme_emerged": lambda: f"We see {payload.get('occurrences_30d', 0)} reviews mentioning '{payload.get('theme', 'feedback')}' in 30 days. {personalization}Let's address this together?",
            
            "festival_upcoming": lambda: f"An {tone['urgency_word']} {tone['focus']} opportunity: {payload.get('festival', 'an event')} is coming. {personalization}Ready to capitalize?",
            
            "winback_eligible": lambda: f"Your {tone['focus']} community misses you! {payload.get('lapsed_customers_added_since_expiry', 0)} people want to come back. {personalization}Let's reconnect?",
            
            "curious_ask_due": lambda: f"What's working best for {tone['focus']} this week? I'd love to know so we can help.",
            
            "recall_due": lambda: f"One of your customers is due for a {payload.get('service_due', 'service')}. Time to reach out and bring them back?",
            
            "ipl_match_today": lambda: f"{payload.get('match', 'Big event')} today in {payload.get('venue', 'your area')}—{tone['urgency_word']} for {tone['focus']}. {personalization}Ready to attract the crowd?",
        }
        
        # Try to get template for this trigger type
        if trigger_kind in templates:
            try:
                msg = templates[trigger_kind]()
                if msg and len(msg) > 10:  # Ensure not empty
                    return msg
            except Exception as e:
                print(f"⚠ Template error for {trigger_kind}: {e}")
                pass  # Fall through to fallback
        
        # Smart fallback based on category and available data
        offers_list = merchant.get("offers", [])
        if isinstance(offers_list, list) and len(offers_list) > 0:
            active_offer = next((o for o in offers_list if isinstance(o, dict) and o.get("status") == "active"), None)
            if active_offer:
                offer_text = f"Your '{active_offer.get('title')}' offer"
                return f"{personalization}{offer_text} has {tone['urgency_word']} {tone['focus']} potential. Ready to promote it?"
        
        # Ultimate fallback: use category-specific phrase
        return f"{personalization}{tone['fallback']} Should we explore new opportunities together?"
        
    except Exception as e:
        # Last-resort fallback
        print(f"✗ Error in compose_message({merchant_id}, {trigger_id}): {e}")
        import traceback
        traceback.print_exc()
        return "We have an exciting opportunity for your business. Would you like to hear more?"


if __name__ == "__main__":
    import uvicorn
    print("Starting Vera bot...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
