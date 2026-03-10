---
title: "CAP Theorem and Distributed Consistency Trade-offs"
type: concept
domain: system-design
level: advanced
status: active
tags: [cap-theorem, consistency, availability, distributed-systems, trade-offs]
related:
  - "[[Microservices_Architecture_Patterns]]"
  - "[[Event_Driven_Architecture_Design]]"
  - "[[Data_Modeling_Patterns_Analytical_Databases]]"
created: 2026-03-10
updated: 2026-03-10
---

## Overview

The CAP theorem states that a distributed system can provide at most two of three guarantees simultaneously: Consistency, Availability, and Partition Tolerance. Understanding these trade-offs is foundational to distributed system design.

## The Three Properties

### Consistency (C)
Every read receives the most recent write or an error. All nodes see the same data at the same time.

### Availability (A)
Every request receives a (non-error) response — but the response may not contain the most recent data.

### Partition Tolerance (P)
The system continues operating even when network partitions prevent some nodes from communicating.

## The Trade-off

**Network partitions are unavoidable in distributed systems.** Therefore, the real choice is between:

- **CP systems** — Choose consistency over availability during partitions
- **AP systems** — Choose availability over consistency during partitions

## CP vs AP in Practice

| System Type | Examples | Behavior During Partition |
|------------|---------|--------------------------|
| CP | HBase, MongoDB (w: majority), ZooKeeper | Returns error rather than stale data |
| AP | Cassandra, DynamoDB, CouchDB | Returns stale data rather than error |
| CA (theoretical) | Single-node RDBMS | Cannot tolerate partitions |

## Consistency Models

### Strong Consistency
All nodes see the same data simultaneously. After write completes, any read returns the written value. High latency.

### Eventual Consistency
Given no new updates, all replicas will converge to the same value — eventually. Low latency, high availability.

### Causal Consistency
Causally related operations are seen in the same order by all nodes. Operations without causal relationship may be seen in different orders.

### Read-Your-Writes
After a write, the same client will always read the written value. Other clients may see stale data.

## PACELC Model

An extension of CAP that addresses latency trade-offs during normal operation:

```
If Partition:     Availability vs Consistency
Else (normal):    Latency vs Consistency
```

This is more practical — even without partitions, there's a trade-off between low latency (AP-like) and strong consistency (CP-like).

## Practical Decisions

### Choose Strong Consistency When
- Financial transactions (banking, payments)
- Inventory management (prevent overselling)
- Authentication systems (security-critical)

### Choose Eventual Consistency When
- Social media feeds
- Product catalog reads
- Analytics and reporting
- Recommendation systems

## Implementation Patterns

### Vector Clocks
Track causality between events in distributed systems without global time synchronization.

### Conflict-Free Replicated Data Types (CRDTs)
Data structures designed to merge concurrent updates deterministically without coordination.

### Two-Phase Commit (2PC)
Distributed transaction protocol for strong consistency. High latency, blocking on coordinator failure.

### Saga Pattern
Distributed transactions via compensating actions. Eventual consistency with explicit rollback logic.

## Conclusion

CAP forces an explicit architectural choice. Partition tolerance is non-negotiable in real distributed systems. Design around either CP or AP based on your domain's tolerance for stale data vs unavailability. Use eventual consistency by default and strong consistency only where the business demands it.
