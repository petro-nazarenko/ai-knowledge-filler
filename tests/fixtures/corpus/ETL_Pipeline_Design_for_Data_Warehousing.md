---
title: "ETL Pipeline Design for Data Warehousing"
type: guide
domain: data-engineering
level: intermediate
status: active
version: v1.0
tags: [etl, data-warehousing, pipeline, data-engineering, sql]
related:
  - "[[Data_Modeling_Patterns_Analytical_Databases]]"
  - "[[Stream_Processing_vs_Batch_Processing]]"
  - "[[Feature_Engineering_Best_Practices]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to designing robust ETL (Extract, Transform, Load) pipelines for data warehousing — covering extraction patterns, transformation best practices, loading strategies, and orchestration.

## Prerequisites

- Basic SQL knowledge
- Understanding of relational and columnar databases
- Access to source systems and a target data warehouse

## ETL vs ELT

| Aspect | ETL | ELT |
|--------|-----|-----|
| Transform location | Before loading | After loading |
| Best for | Legacy warehouses | Cloud warehouses (BigQuery, Snowflake) |
| Flexibility | Fixed schema required | Schema-on-read possible |
| Compute | ETL tool | Warehouse compute |

**Modern recommendation:** ELT for cloud warehouses (transform in SQL).

## Step 1: Extraction Patterns

### Full Extract
```sql
-- Extract entire table (small tables, daily loads)
SELECT * FROM source.orders;
```

### Incremental Extract (Preferred)
```sql
-- Extract only new/changed records
SELECT *
FROM source.orders
WHERE updated_at > :last_run_timestamp;
```

### CDC (Change Data Capture)
Stream database transaction log for near-real-time capture. Tools: Debezium, AWS DMS, Fivetran.

## Step 2: Transformation Layer

### Data Quality Checks

```python
def validate_extract(df):
    assert df["order_id"].notnull().all(), "Null order IDs"
    assert df["order_date"].dtype == "datetime64[ns]", "Invalid date type"
    assert (df["amount"] >= 0).all(), "Negative amounts"
    return df
```

### Deduplication

```sql
-- Remove duplicates using row_number window function
WITH deduped AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY order_id
      ORDER BY updated_at DESC
    ) AS rn
  FROM staging.orders
)
SELECT * FROM deduped WHERE rn = 1;
```

### Dimension Slowly Changing (SCD Type 2)

```sql
-- Track history: add new row instead of updating
INSERT INTO dim_customer
SELECT
  customer_id,
  email,
  CURRENT_DATE AS effective_from,
  NULL AS effective_to,
  TRUE AS is_current
FROM staging.customers
WHERE customer_id NOT IN (
  SELECT customer_id FROM dim_customer WHERE is_current = TRUE
);
```

## Step 3: Load Strategies

### Truncate and Reload
Simple, reliable for small tables. No incremental tracking needed.

### Append Only
For immutable event data (logs, transactions).

### Upsert (Merge)
```sql
MERGE INTO warehouse.orders AS target
USING staging.orders AS source
  ON target.order_id = source.order_id
WHEN MATCHED THEN
  UPDATE SET amount = source.amount, status = source.status
WHEN NOT MATCHED THEN
  INSERT (order_id, amount, status, created_at)
  VALUES (source.order_id, source.amount, source.status, source.created_at);
```

## Orchestration

### Tools

| Tool | Type | Use Case |
|------|------|----------|
| Apache Airflow | DAG-based | Complex pipelines, many dependencies |
| dbt | SQL-first | ELT transformations |
| Prefect | Python-native | Data science workflows |
| AWS Glue | Managed | AWS-native pipelines |

### DAG Design Principles
- Each task is idempotent (safe to retry)
- Tasks are atomic (all-or-nothing)
- Dependencies are explicit
- Failure alerts notify on-call

## Data Quality Framework

```python
# Great Expectations example
import great_expectations as gx

context = gx.get_context()
suite = context.add_expectation_suite("orders_suite")

suite.add_expectation(
    gx.ExpectColumnValuesToNotBeNull(column="order_id")
)
suite.add_expectation(
    gx.ExpectColumnValuesToBeBetween(column="amount", min_value=0)
)
```

## Conclusion

Well-designed ETL pipelines are idempotent, observable, and validated at each stage. Prefer ELT with cloud warehouses to leverage SQL for transformations. Invest in data quality checks early — bad data costs more to fix downstream.
