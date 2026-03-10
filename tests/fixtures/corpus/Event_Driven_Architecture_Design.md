---
title: "Event-Driven Architecture Design with Message Queues"
type: guide
domain: system-design
level: advanced
status: active
version: v1.0
tags: [event-driven, architecture, message-queues, async, distributed-systems]
related:
  - "[[Microservices_Architecture_Patterns]]"
  - "[[CAP_Theorem_and_Distributed_Consistency]]"
  - "[[ETL_Pipeline_Design]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to designing event-driven architectures using message queues — covering event schema design, producer/consumer patterns, delivery guarantees, and operational best practices.

## Prerequisites

- Understanding of synchronous vs asynchronous communication
- Familiarity with at least one message broker (Kafka, RabbitMQ, SQS)
- Basic distributed systems concepts

## Core Concepts

### Event
An immutable record of something that happened.

```json
{
  "event_id": "evt-001",
  "event_type": "order.placed",
  "timestamp": "2026-03-10T12:00:00Z",
  "source": "orders-service",
  "data": {"order_id": "123", "total": 49.99}
}
```

### Message Queue vs Event Stream

| Feature | Queue (RabbitMQ, SQS) | Stream (Kafka) |
|---------|----------------------|----------------|
| Consumption | One consumer | Multiple consumers |
| Retention | Until consumed | Configurable (days/weeks) |
| Replay | No | Yes |
| Ordering | Per-queue | Per-partition |
| Use case | Task distribution | Event sourcing, analytics |

## Step 1: Design Event Schema

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DomainEvent:
    event_id: str
    event_type: str       # noun.verb: order.placed, user.registered
    source: str           # originating service
    timestamp: datetime
    data: dict
    version: str = "1.0"  # schema version
```

### Event Naming Convention
Use `domain.action` pattern: `order.placed`, `payment.failed`, `user.activated`

## Step 2: Configure Producer

```python
# Kafka producer example
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=["localhost:9092"],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    acks="all",            # wait for all replicas
    retries=3,
    enable_idempotence=True,
)

def publish_event(topic: str, event: DomainEvent):
    producer.send(topic, value=event.__dict__)
    producer.flush()
```

## Step 3: Implement Consumer

```python
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    "order-events",
    bootstrap_servers=["localhost:9092"],
    group_id="inventory-service",
    auto_offset_reset="earliest",
    enable_auto_commit=False,  # manual commit for at-least-once
)

for message in consumer:
    event = json.loads(message.value)
    try:
        handle_event(event)
        consumer.commit()
    except Exception as e:
        send_to_dead_letter_queue(event, e)
```

## Delivery Guarantees

| Guarantee | Risk | Requirement |
|-----------|------|-------------|
| At-most-once | Message loss | Fire-and-forget |
| At-least-once | Duplicate processing | Idempotent consumers |
| Exactly-once | Complexity | Transactions (Kafka) |

**Recommendation:** Design consumers to be idempotent, use at-least-once delivery.

## Dead Letter Queue

Always configure DLQ for unprocessable events:
1. Consumer fails after N retries
2. Event routed to DLQ with error metadata
3. Alerting triggered
4. Manual investigation and replay

## Operational Practices

- **Schema Registry** — Centralize event schema management (Confluent Schema Registry)
- **Consumer Lag Monitoring** — Alert when consumer falls behind
- **Partition Strategy** — Partition by tenant/user ID for ordering guarantees
- **Event Replay** — Design consumers to safely replay events from beginning

## Conclusion

Event-driven architecture decouples services and enables asynchronous processing at scale. Key design decisions: stream vs queue, delivery guarantee, and schema evolution strategy. Always design for idempotent consumers and invest in observability early.
