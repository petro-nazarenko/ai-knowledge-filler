---
title: "Stream Processing vs Batch Processing Trade-offs"
type: concept
domain: data-engineering
level: intermediate
status: active
tags: [stream-processing, batch-processing, data-engineering, trade-offs, latency]
related:
  - "[[ETL_Pipeline_Design_for_Data_Warehousing]]"
  - "[[Event_Driven_Architecture_Design]]"
  - "[[Data_Modeling_Patterns_Analytical_Databases]]"
created: 2026-03-10
updated: 2026-03-10
---

## Overview

Stream processing and batch processing are two paradigms for handling data at scale. The choice between them depends on latency requirements, data volume, and operational complexity tolerance.

## Core Differences

| Dimension | Batch | Stream |
|-----------|-------|--------|
| Latency | Minutes to hours | Milliseconds to seconds |
| Throughput | Very high | High |
| Complexity | Low | High |
| Error handling | Retry entire batch | Complex exactly-once semantics |
| Backfill | Trivial | Difficult |
| Cost | Lower compute | Higher infrastructure |
| Fault tolerance | Simple | Complex (checkpointing) |

## Batch Processing

### When to Use
- Daily/weekly reports
- ML model training
- Data warehouse loads
- Compliance reporting
- Large historical analysis

### Architecture

```
Source Data → Extract → Transform → Load → Report
(hourly/daily schedule)
```

### Tools

| Tool | Use Case |
|------|----------|
| Apache Spark | Large-scale distributed processing |
| dbt | SQL-first warehouse transformations |
| Apache Flink (batch mode) | Unified batch and stream |
| Python + Pandas | Small-medium datasets |
| AWS Glue | Managed Spark on AWS |

### Batch Pattern: Idempotent Processing

```python
def process_batch(date: str):
    # Idempotent: safe to re-run for same date
    data = extract(date)
    transformed = transform(data)
    # Truncate partition before loading
    delete_partition(date)
    load(transformed, partition=date)
```

## Stream Processing

### When to Use
- Real-time dashboards
- Fraud detection (millisecond decisions)
- Event-driven microservices
- Real-time personalization
- IoT sensor data

### Architecture

```
Source → Message Broker → Stream Processor → Sink
(Kafka)   (Kafka Streams/Flink)   (DB/Cache)
```

### Tools

| Tool | Latency | Throughput |
|------|---------|-----------|
| Apache Kafka Streams | Low | High |
| Apache Flink | Very low | Very high |
| Apache Spark Streaming | Medium | High |
| AWS Kinesis | Low | High |

### Delivery Guarantees

| Guarantee | Complexity | Use Case |
|-----------|------------|----------|
| At-most-once | Low | Metrics (loss acceptable) |
| At-least-once | Medium | Most pipelines (idempotent sink) |
| Exactly-once | High | Financial transactions |

## Lambda Architecture (Hybrid)

Combines batch and stream layers:
```
            Serving Layer
           /             \
Batch Layer              Speed Layer
(high accuracy)          (low latency)
```

**Drawback:** Two codebases to maintain.

## Kappa Architecture (Stream-Only)

Stream layer replaces batch layer by using replayable event log (Kafka):
```
Event Log → Stream Processing → Serving Layer
```

Backfill by replaying from beginning of log.

## Decision Framework

```
Latency requirement?
  < 1 second  → Stream
  1–60 seconds → Micro-batch
  > 1 minute   → Batch

Data volume?
  < 1GB/hour → Batch (simple)
  > 1GB/hour → Consider stream or distributed batch

Error tolerance?
  Need exactly-once? → Batch (simpler) or Flink
  At-least-once OK? → Kafka Streams
```

## Conclusion

Batch processing is the right default — lower complexity and easier debugging. Adopt stream processing only when latency requirements genuinely demand it. Most analytics workloads are better served by batch, with micro-batch as a pragmatic middle ground.
