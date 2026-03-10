---
title: "Cloud Infrastructure Cost Optimization on AWS"
type: reference
domain: devops
level: intermediate
status: active
version: v1.0
tags: [aws, cost-optimization, cloud, infrastructure, finops]
related:
  - "[[Kubernetes_Deployment_Readiness]]"
  - "[[Docker_Multi_Stage_Builds]]"
  - "[[Observability_Stack_Design]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Reference for AWS infrastructure cost optimization — covering compute, storage, network, and database cost reduction strategies with practical implementation guidance.

## Cost Visibility First

Before optimizing, establish visibility:
- Enable **AWS Cost Explorer** with daily granularity
- Configure **AWS Budgets** with alerts at 80% and 100% of budget
- Enable **Cost Allocation Tags** on all resources
- Use **AWS Trusted Advisor** for quick wins

## Compute Optimization

### EC2 Right-Sizing

```
Step 1: Enable CloudWatch agent for memory metrics
Step 2: Run Cost Explorer right-sizing recommendations
Step 3: Down-size instances with <20% avg CPU over 14 days
Step 4: Monitor post-resize for 1 week
```

### Reserved Instances and Savings Plans

| Type | Discount | Commitment | Flexibility |
|------|----------|------------|-------------|
| On-Demand | 0% | None | Maximum |
| Compute Savings Plan | Up to 66% | 1–3 year | High (any EC2/Fargate/Lambda) |
| EC2 Instance Savings Plan | Up to 72% | 1–3 year | Medium (instance family) |
| Reserved Instances | Up to 75% | 1–3 year | Low (specific instance type) |

**Rule:** Purchase Savings Plans for baseline workload, use Spot for batch/flexible workloads.

### Spot Instances

Up to 90% discount for interruptible workloads:
- **Suitable:** Batch jobs, CI/CD workers, ML training, stateless services
- **Unsuitable:** Stateful databases, user-facing services without failover
- Implement Spot interruption handler (2-minute warning)

### Lambda Optimization

```python
# Right-size memory (compute scales linearly with memory)
# Profile at different memory settings to find cost-performance sweet spot
# Use ARM (Graviton2) for 20% better price-performance
```

## Container (ECS/EKS) Cost

```yaml
# Fargate Spot for batch tasks
resources:
  requests:
    cpu: "100m"    # Don't over-provision
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "256Mi"
```

- Use **Karpenter** for intelligent node provisioning (replaces Cluster Autoscaler)
- Mix Spot and On-Demand node groups
- Set accurate resource requests (over-provisioning wastes money)

## Storage Optimization

### S3

```
Lifecycle policies:
  0–30 days:    S3 Standard
  30–90 days:   S3 Standard-IA
  90–365 days:  S3 Glacier Instant
  >365 days:    S3 Glacier Deep Archive
```

- Enable S3 Intelligent-Tiering for access pattern uncertainty
- Enable S3 Inventory + S3 Analytics to find optimization opportunities
- Delete incomplete multipart uploads (lifecycle rule)

### EBS Volumes

- Delete unattached volumes (common source of waste)
- Migrate gp2 → gp3 (same price, better performance)
- Snapshot lifecycle policies for automated cleanup

## Database Optimization

### RDS

- Use Aurora Serverless v2 for variable workloads (auto-scales compute)
- Stop non-production RDS instances outside business hours
- Use read replicas for read-heavy workloads (offload primary)

### ElastiCache

- Right-size node types based on memory usage, not peak
- Use **eviction metrics** to detect undersizing
- Reserved nodes for steady-state cache usage

## Network Costs

Often overlooked but significant:
- **Data transfer out** to internet: $0.09/GB in most regions
- **Cross-AZ traffic:** $0.01/GB each direction
- **Use VPC endpoints** for S3/DynamoDB (free, avoids NAT Gateway)
- **CloudFront** for frequently accessed content (cheaper than direct S3)

## Cost Governance

- Implement **tag policies** to enforce mandatory tags (project, env, owner)
- Use **AWS Organizations SCPs** to prevent accidental expensive resources
- Monthly cost review with team leads
- **Anomaly Detection** — alert on unexpected cost spikes (>20% week-over-week)

## Conclusion

Cloud cost optimization is continuous, not a one-time project. Start with visibility (tagging + Cost Explorer), take quick wins (right-size, stop unused), then implement reservation strategy for steady-state workloads. Target: 30–40% cost reduction is achievable in most organizations within 90 days.
