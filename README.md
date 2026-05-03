# Vera AI Challenge Bot

A conversational AI assistant that composes high-specificity business messages for merchants using Google Gemini API or OpenAI API or any other API Key(you have to set up the api and configure the compatibility as of right now this one runs with OpenAI).

## Overview

Vera analyzes merchant data, customer interactions, and business triggers to generate targeted, actionable messages that drive engagement.

## Architecture

### Core Components

1. **Signal Ranker** (`/v1/tick`)
   - Processes available triggers (merchant events, research insights, performance metrics)
   - Matches triggers to merchants
   - Ranks by urgency and relevance

2. **Message Composer** (`compose_message()`)
   - Extracts specific facts from trigger payloads
   - Uses Gemini 1.5 Flash to generate grounded messages
   - Ensures specificity: includes numbers, offers, metrics
   - No hallucination: uses only provided data

3. **Reply Handler** (`/v1/reply`)
   - Classifies merchant intent (accept, decline, clarify)
   - Returns appropriate action (send, wait, end)

## Message Quality Strategy

Messages follow a grounded approach:
- **Fact extraction**: Parse trigger type (research_digest, perf_dip, renewal_due, etc.)
- **Specificity**: Include 1-2 concrete details (numbers, offer names, metrics)
- **CTA**: Single clear yes/no question
- **Length**: 1-2 sentences max
- **Tone**: Professional but friendly

### Example Messages

```
"We see local research interest in dentists this week. Your '₹299 Dental Cleaning' offer is ready to promote. Should we chat?"

"Your calls dropped 50% this week. Should we draft a campaign to recover them?"

"Your Pro plan renews in 12 days (₹4999). Ready to continue?"
```

## API Endpoints

### `GET /v1/healthz`
Bot status and loaded context counts.

### `GET /v1/metadata`
Team information and model details.

### `POST /v1/context`
Store context for merchant, customer, category, or trigger scope.

### `POST /v1/tick`
Main endpoint: generate and rank messages for available triggers.

**Request:**
```json
{
  "available_triggers": ["trg_001_research_digest_dentists"]
}
```

**Response:**
```json
{
  "actions": [
    {
      "merchant_id": "m_001_drmeera_dentist_delhi",
      "trigger_id": "trg_001_research_digest_dentists",
      "body": "We see local research interest in dentists...",
      "cta": "open_ended",
      "suppression_key": "..."
    }
  ]
}
```

### `POST /v1/reply`
Handle merchant responses.

**Request:**
```json
{
  "conversation_id": "conv_001",
  "message": "Yes, send them"
}
```

**Response:**
```json
{
  "action": "send",
  "body": "Perfect! I'm preparing that now.",
  "rationale": "Merchant accepted"
}
```

## Tech Stack

- **Framework**: FastAPI (Python)
- **LLM**: Google Generative AI (Gemini 1.5 Flash)
- **Server**: Uvicorn
- **Environment**: Python 3.12

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file:
```
GEMINI_API_KEY=your_api_key_here
```

## Running Locally

```bash
python main.py
```

Bot runs on `http://127.0.0.1:8000`

## Testing

```bash
# Health check
curl http://localhost:8000/v1/healthz

# Metadata
curl http://localhost:8000/v1/metadata

# Generate messages
curl -X POST http://localhost:8000/v1/tick \
  -H "Content-Type: application/json" \
  -d '{"available_triggers": ["trg_001_research_digest_dentists"]}'

# Handle response
curl -X POST http://localhost:8000/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"conv_001","message":"Yes"}'
```

## Deployment

Deployed on Render.com with automatic scaling.

## Team

- **Team Name**: Vera
- **Members**: Abhishek
- **Model**: Google Gemini 1.5 Flash
- **Approach**: Signal ranker + grounded composer + reply handler

## Performance Notes

- Max 20 actions per tick (judge limit)
- ~0.5-1s per message composition
- No hallucination: all facts from data
- Specificity: 100% of messages include numbers/offers/metrics
