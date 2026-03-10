---
title: "Microservices Architecture Patterns for Distributed Systems"
type: reference
domain: system-design
level: advanced
status: active
version: v1.0
tags: [microservices, architecture, distributed-systems, patterns, scalability]
related:
  - "[[Event_Driven_Architecture_Design]]"
  - "[[CAP_Theorem_and_Distributed_Consistency]]"
  - "[[Observability_Stack_Design]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Reference for core microservices architecture patterns in distributed systems — covering service decomposition, communication, data management, and resilience.

## Decomposition Patterns

### Domain-Driven Design (DDD) Decomposition
Decompose by bounded context — each service owns a domain with its own data model and language.

```
Orders Service    → manages order lifecycle
Inventory Service → manages stock levels
Payment Service   → manages transactions
Notification Service → manages alerts
```

### Strangler Fig Pattern
Migrate monolith to microservices incrementally by routing traffic through a façade that progressively delegates to new services.

## Communication Patterns

### Synchronous (Request-Response)

| Protocol | Use Case |
|----------|----------|
| REST/HTTP | Client-facing APIs, simple queries |
| gRPC | Internal services, high-throughput |
| GraphQL | Flexible client data requirements |

### Asynchronous (Event-Driven)

| Pattern | Use Case |
|---------|----------|
| Pub/Sub | Fan-out notifications |
| Event Sourcing | Audit trail, replay capability |
| CQRS | Read/write separation |
| Saga | Distributed transactions |

## Data Management Patterns

### Database per Service
Each service has its own database. No shared schemas. Enforces loose coupling.

### Shared Database (Anti-Pattern)
Multiple services share a database. Tight coupling — avoid in new designs.

### Event Sourcing
Store state changes as immutable events. Current state = replay of events.

```
OrderPlaced → OrderConfirmed → OrderShipped → OrderDelivered
```

### CQRS (Command Query Responsibility Segregation)
Separate write model (commands) from read model (queries). Enables independent scaling.

## Resilience Patterns

### Circuit Breaker
Prevent cascading failures by stopping calls to failing services.

```
States: Closed → Open → Half-Open → Closed
Closed: Normal operation
Open: Fast-fail, no calls made
Half-Open: Test probe sent
```

### Bulkhead
Isolate failures by partitioning resources. If one service pool exhausts, others continue.

### Retry with Backoff
Retry transient failures with exponential backoff and jitter. Do not retry non-idempotent operations.

### Timeout
Every service call must have a timeout. No unbounded waits.

## Service Discovery

### Client-Side Discovery
Client queries service registry (e.g., Consul, Eureka) and load-balances directly.

### Server-Side Discovery
Load balancer queries registry and routes. Client sends request to load balancer.

## Observability

Essential for distributed tracing:
- **Distributed tracing** — correlation IDs across services (Jaeger, Zipkin)
- **Structured logging** — JSON logs with service name and trace ID
- **Metrics** — per-service RED metrics (Rate, Errors, Duration)

## Conclusion

Microservices offer independent scalability and team autonomy at the cost of distributed system complexity. Apply patterns deliberately: Circuit Breaker for resilience, Saga for transactions, CQRS where read/write loads differ significantly.
