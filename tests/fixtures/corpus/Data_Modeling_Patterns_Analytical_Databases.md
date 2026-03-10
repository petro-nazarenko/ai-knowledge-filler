---
title: "Data Modeling Patterns for Analytical Databases"
type: reference
domain: data-engineering
level: intermediate
status: active
version: v1.0
tags: [data-modeling, analytics, warehouse, dimensional, olap]
related:
  - "[[ETL_Pipeline_Design_for_Data_Warehousing]]"
  - "[[Stream_Processing_vs_Batch_Processing]]"
  - "[[Feature_Engineering_Best_Practices]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Reference for data modeling patterns in analytical databases — covering dimensional modeling, schema types, and modern warehouse-native approaches.

## OLTP vs OLAP Modeling

| Aspect | OLTP | OLAP |
|--------|------|------|
| Purpose | Transactional | Analytical |
| Normalization | High (3NF) | Low (denormalized) |
| Query type | Point lookups | Aggregations, scans |
| Write pattern | Frequent updates | Bulk loads |
| Join count | Many | Few (pre-joined) |
| Example | PostgreSQL | Snowflake, BigQuery |

## Dimensional Modeling

### Star Schema

```
          dim_date
              |
dim_customer—fact_sales—dim_product
              |
         dim_location
```

**Fact table:** Numeric measures (revenue, quantity, duration)
**Dimension tables:** Descriptive attributes (who, what, when, where)

**Advantages:**
- Simple queries
- Excellent aggregation performance
- Business-user friendly

### Snowflake Schema

Dimensions normalized into sub-dimensions:

```
dim_customer → dim_region → dim_country
```

**Advantages:** Less storage redundancy
**Disadvantages:** More joins, slower queries

### One Big Table (OBT)

Fully denormalized single table. Common in modern cloud warehouses.

```sql
SELECT
  order_date,
  customer_name,
  product_category,
  SUM(revenue)
FROM analytics.orders_flat  -- single denormalized table
GROUP BY 1, 2, 3;
```

## Fact Table Types

| Type | Description | Example |
|------|-------------|---------|
| Transaction | One row per event | Order placed |
| Periodic snapshot | State at intervals | Daily balance |
| Accumulating snapshot | Lifecycle tracking | Order → shipped → delivered |

## Slowly Changing Dimensions (SCD)

### SCD Type 1 — Overwrite
Update in place. No history. Simple.

### SCD Type 2 — Add New Row (Most Common)
```
| customer_id | email | effective_from | effective_to | is_current |
|-------------|-------|----------------|--------------|------------|
| 1 | old@example.com | 2024-01-01 | 2026-01-15 | false |
| 1 | new@example.com | 2026-01-15 | NULL | true |
```

### SCD Type 3 — Add Column
Store previous value as a separate column.

## Metrics Layer (Semantic Layer)

Modern warehouses use a semantic layer (dbt Metrics, Looker LookML) to:
- Define business metrics once
- Reuse across dashboards and queries
- Enforce consistent calculation logic

```yaml
# dbt metric definition
metrics:
  - name: monthly_revenue
    label: Monthly Revenue
    model: ref('fact_orders')
    calculation_method: sum
    expression: revenue
    timestamp: order_date
    time_grains: [month, quarter, year]
```

## Partitioning and Clustering

### Partitioning
Divide table by column value (date, region). Queries on partition key scan less data.

```sql
CREATE TABLE orders
PARTITION BY DATE(order_date);
```

### Clustering
Sort data within partitions by column. Reduces bytes scanned for filter queries.

```sql
CREATE TABLE orders
CLUSTER BY (customer_id, product_id);
```

## Conclusion

Star schema dimensional modeling is the industry standard for analytical databases. Modern cloud warehouses (BigQuery, Snowflake) favor denormalized designs and leverage compute to outperform normalized schemas. Invest in SCD Type 2 for critical business dimensions that need historical analysis.
