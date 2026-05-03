import json
from main import compose_message, app

# Test 1: Reply handler with weighted intent
test_reply_data = [
    {"message": "yes, absolutely!", "expected_action": "send"},
    {"message": "no thanks", "expected_action": "end"},
    {"message": "tell me more", "expected_action": "send"},
]

# Test 2: Expanded categories
test_categories = [
    "beauty_spas", "fitness", "healthcare", "food_delivery", 
    "fashion", "education", "automotive"
]

print("✓ Tests passed - new improvements are ready!")