#!/bin/bash

# Vera Bot - Manual Testing Script
# Usage: ./manual_tests.sh
# Tests all endpoints with curl and validates responses

BASE_URL="http://localhost:8000"
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Vera Bot - Manual Test Cases${NC}"
echo -e "${BLUE}========================================${NC}\n"

# TEST 1: Health Check
echo -e "${BLUE}TEST 1: /v1/healthz - Check bot is running${NC}"
echo "Command: curl -s $BASE_URL/v1/healthz | python -m json.tool"
curl -s $BASE_URL/v1/healthz | python -m json.tool
echo -e "\n"

# TEST 2: Metadata Check
echo -e "${BLUE}TEST 2: /v1/metadata - Check team info & model${NC}"
echo "Command: curl -s $BASE_URL/v1/metadata | python -m json.tool"
curl -s $BASE_URL/v1/metadata | python -m json.tool
echo -e "\n"

# TEST 3: Positive Intent
echo -e "${BLUE}TEST 3: /v1/reply - Positive Intent (High Confidence)${NC}"
echo "Message: 'Yes, absolutely! Let's do it.'"
echo "Expected: action=send, reason_code=explicit_accept, confidence > 0.8"
curl -s -X POST $BASE_URL/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "Yes, absolutely! Let'"'"'s do it.", "conversation_id": "conv_001"}' | python -m json.tool
echo -e "\n"

# TEST 4: Negative Intent
echo -e "${BLUE}TEST 4: /v1/reply - Negative Intent (High Confidence)${NC}"
echo "Message: 'No, I'm not interested.'"
echo "Expected: action=end, reason_code=explicit_decline, confidence > 0.8"
curl -s -X POST $BASE_URL/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "No, I'"'"'m not interested.", "conversation_id": "conv_002"}' | python -m json.tool
echo -e "\n"

# TEST 5: Unclear Intent
echo -e "${BLUE}TEST 5: /v1/reply - Unclear Intent (Clarification)${NC}"
echo "Message: 'Tell me more about this.'"
echo "Expected: action=send, reason_code=unclear_intent, confidence < 0.6"
curl -s -X POST $BASE_URL/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me more about this.", "conversation_id": "conv_003"}' | python -m json.tool
echo -e "\n"

# TEST 6: Empty Message
echo -e "${BLUE}TEST 6: /v1/reply - Empty Message (Clarification)${NC}"
echo "Message: ''"
echo "Expected: action=send, reason_code=unclear_intent"
curl -s -X POST $BASE_URL/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "", "conversation_id": "conv_004"}' | python -m json.tool
echo -e "\n"

# TEST 7: Case Insensitive
echo -e "${BLUE}TEST 7: /v1/reply - Case Insensitive Matching${NC}"
echo "Message: 'YeS'"
echo "Expected: reason_code=explicit_accept despite mixed case"
curl -s -X POST $BASE_URL/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "YeS", "conversation_id": "conv_005"}' | python -m json.tool
echo -e "\n"

# TEST 8: Multiple Signals
echo -e "${BLUE}TEST 8: /v1/reply - Weighted Scoring (Multiple Signals)${NC}"
echo "Message: 'Yeah, I'"'"'m interested! Let'"'"'s go.'"
echo "Expected: confidence=0.95 (max) due to multiple positive signals"
curl -s -X POST $BASE_URL/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "Yeah, I'"'"'m interested! Let'"'"'s go.", "conversation_id": "conv_006"}' | python -m json.tool
echo -e "\n"

# TEST 9: Medium Confidence
echo -e "${BLUE}TEST 9: /v1/reply - Medium Confidence (Weak Signal)${NC}"
echo "Message: 'Maybe later.'"
echo "Expected: reason_code=explicit_decline, 0.6 <= confidence <= 0.8"
curl -s -X POST $BASE_URL/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"message": "Maybe later.", "conversation_id": "conv_007"}' | python -m json.tool
echo -e "\n"

# TEST 10: Trigger Ranking
echo -e "${BLUE}TEST 10: /v1/tick - Trigger Ranking${NC}"
echo "Processing triggers: ['trg_001', 'trg_002', 'trg_003']"
echo "Expected: actions sorted by urgency"
curl -s -X POST $BASE_URL/v1/tick \
  -H "Content-Type: application/json" \
  -d '{"available_triggers": ["trg_001", "trg_002", "trg_003"]}' | python -m json.tool
echo -e "\n"

# TEST 11: Category-Aware Messages
echo -e "${BLUE}TEST 11: /v1/tick - Category-Aware Messages${NC}"
echo "First, setting merchant context with restaurant category..."
curl -s -X POST $BASE_URL/v1/context \
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
  }' | python -m json.tool

echo "Now checking if messages are category-specific..."
curl -s -X POST $BASE_URL/v1/tick \
  -H "Content-Type: application/json" \
  -d '{"available_triggers": ["trg_test_001"]}' | python -m json.tool
echo -e "\n"

# TEST 12: Error Resilience
echo -e "${BLUE}TEST 12: /v1/reply - Error Resilience (Malformed Input)${NC}"
echo "Message: Malformed JSON (missing message field)"
echo "Expected: Clear error or safe fallback response"
curl -s -X POST $BASE_URL/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "conv_008"}' | python -m json.tool
echo -e "\n"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All tests completed!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${BLUE}Summary:${NC}"
echo "✅ If all responses are valid JSON, tests passed"
echo "✅ Check TESTING.md for expected values"
echo "✅ Confidence scores should be between 0.0 and 0.95"
echo "✅ reason_code should be one of: explicit_accept, explicit_decline, unclear_intent"

