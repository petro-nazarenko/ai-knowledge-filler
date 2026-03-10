---
title: "Workflow Automation Design with Python and Webhooks"
type: guide
domain: backend-engineering
level: intermediate
status: active
version: v1.0
tags: [automation, webhooks, python, workflow, integration]
related:
  - "[[Backend_Service_Architecture_FastAPI]]"
  - "[[No_Code_Integration_Patterns]]"
  - "[[Event_Driven_Architecture_Design]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to designing workflow automation systems using Python and webhooks — covering webhook receivers, event routing, state machines, and reliability patterns.

## Prerequisites

- Python 3.10+, FastAPI
- Basic understanding of HTTP and REST
- Familiarity with at least one external service (GitHub, Stripe, Slack)

## Webhook Fundamentals

Webhooks are HTTP callbacks — when an event occurs in system A, it sends an HTTP POST to system B's registered URL.

```
External Service → POST /webhook → Your Handler → Process Event
    GitHub              →         /github/events   → Create PR comment
    Stripe              →         /stripe/events   → Update payment status
    Slack               →         /slack/events    → Process command
```

## Step 1: Webhook Receiver

```python
from fastapi import FastAPI, Request, HTTPException, Header
import hmac, hashlib

app = FastAPI()

@app.post("/github/events")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
):
    body = await request.body()

    # Verify signature
    if not verify_github_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    await route_github_event(x_github_event, payload)
    return {"status": "accepted"}

def verify_github_signature(body: bytes, signature: str) -> bool:
    secret = os.getenv("GITHUB_WEBHOOK_SECRET").encode()
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

## Step 2: Event Router

```python
EVENT_HANDLERS = {}

def register_handler(event_type: str):
    def decorator(func):
        EVENT_HANDLERS[event_type] = func
        return func
    return decorator

async def route_github_event(event_type: str, payload: dict):
    handler = EVENT_HANDLERS.get(event_type)
    if handler:
        await handler(payload)
    else:
        logger.debug("No handler for event: %s", event_type)

@register_handler("pull_request")
async def handle_pr(payload: dict):
    action = payload["action"]
    if action == "opened":
        await notify_team(payload)
    elif action == "closed" and payload["pull_request"]["merged"]:
        await trigger_deployment(payload)
```

## Step 3: State Machine

For multi-step workflows:

```python
from enum import Enum

class OrderState(Enum):
    PENDING = "pending"
    PAYMENT_PROCESSING = "payment_processing"
    CONFIRMED = "confirmed"
    FULFILLING = "fulfilling"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

VALID_TRANSITIONS = {
    OrderState.PENDING: [OrderState.PAYMENT_PROCESSING, OrderState.CANCELLED],
    OrderState.PAYMENT_PROCESSING: [OrderState.CONFIRMED, OrderState.CANCELLED],
    OrderState.CONFIRMED: [OrderState.FULFILLING, OrderState.CANCELLED],
    OrderState.FULFILLING: [OrderState.SHIPPED],
    OrderState.SHIPPED: [OrderState.DELIVERED],
}

def transition(current: OrderState, next_state: OrderState) -> OrderState:
    if next_state not in VALID_TRANSITIONS.get(current, []):
        raise ValueError(f"Invalid transition: {current} → {next_state}")
    return next_state
```

## Step 4: Reliability Patterns

### Idempotency
Webhooks are delivered at-least-once. Handle duplicates:

```python
processed_events = set()  # Use Redis in production

async def handle_stripe_payment(payload: dict):
    event_id = payload["id"]
    if event_id in processed_events:
        return  # Duplicate — ignore
    processed_events.add(event_id)
    await process_payment(payload)
```

### Async Processing with Queue

```python
from asyncio import Queue

event_queue: Queue = Queue()

@app.post("/webhook")
async def receive_webhook(request: Request):
    payload = await request.json()
    await event_queue.put(payload)  # Fast acknowledgment
    return {"status": "queued"}  # Return 200 immediately

async def process_queue():
    while True:
        payload = await event_queue.get()
        try:
            await process_event(payload)
        except Exception as e:
            await send_to_dlq(payload, error=str(e))
```

## Security Requirements

- **Verify signatures** on all incoming webhooks
- **HTTPS only** for webhook endpoints
- **Timeout** — return 200 within 5 seconds (process async)
- **Rate limit** webhook endpoints (prevent abuse)
- **Log all events** for audit trail

## Conclusion

Webhook-driven automation requires fast acknowledgment (return 200 immediately), async processing via queue, idempotency (handle duplicate deliveries), and signature verification. Design state machines for multi-step workflows to ensure valid transitions and prevent inconsistent state.
