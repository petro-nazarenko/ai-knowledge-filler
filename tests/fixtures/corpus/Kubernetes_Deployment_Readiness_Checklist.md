---
title: "Kubernetes Deployment Readiness Review"
type: checklist
domain: devops
level: advanced
status: active
tags: [kubernetes, deployment, readiness, production, checklist]
related:
  - "[[Docker_Multi_Stage_Builds]]"
  - "[[CICD_Pipeline_Design_GitHub_Actions]]"
  - "[[Observability_Stack_Design]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Pre-deployment readiness checklist for Kubernetes workloads. Covers container configuration, resource management, health checks, security, and observability.

## Container Configuration

- [ ] Docker image uses multi-stage build (minimal final image)
- [ ] Image tagged with immutable SHA or version (not `latest`)
- [ ] Non-root user configured in Dockerfile
- [ ] .dockerignore excludes development artifacts
- [ ] No secrets baked into image layers
- [ ] Image scanned for vulnerabilities (Trivy, Snyk)

## Pod Specification

- [ ] Resource requests and limits set for all containers
- [ ] CPU and memory limits are realistic (not 0 or unbounded)
- [ ] `readinessProbe` configured (prevents traffic before ready)
- [ ] `livenessProbe` configured (enables auto-restart on hang)
- [ ] `startupProbe` set for slow-starting containers
- [ ] Pod disruption budget (PDB) defined for critical workloads

## Resource Configuration

```yaml
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

- [ ] Requests match baseline usage (not too low, not too high)
- [ ] Limits set to prevent noisy-neighbor impact
- [ ] Horizontal pod autoscaler (HPA) configured for variable load

## Health Checks

```yaml
readinessProbe:
  httpGet:
    path: /healthz/ready
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5

livenessProbe:
  httpGet:
    path: /healthz/live
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
```

- [ ] `/healthz/ready` returns 200 only when traffic can be served
- [ ] `/healthz/live` returns 200 only when process is not deadlocked
- [ ] Probe timeouts set appropriately

## Secrets and Configuration

- [ ] Secrets stored in Kubernetes Secrets (not ConfigMaps)
- [ ] Secrets mounted as env vars or volume mounts (not hardcoded)
- [ ] Sensitive values not logged at startup
- [ ] External secret management integrated (Vault, AWS Secrets Manager)
- [ ] ConfigMaps used for non-sensitive configuration only

## Networking

- [ ] Service type is appropriate (ClusterIP/LoadBalancer/NodePort)
- [ ] Ingress configured with TLS
- [ ] Network policies restrict ingress/egress to required services only
- [ ] No unnecessary ports exposed

## Deployment Strategy

- [ ] Rolling update strategy configured
- [ ] `maxSurge` and `maxUnavailable` set appropriately
- [ ] Rollback tested and documented
- [ ] Deployment verified in staging before production

## Observability

- [ ] Structured logging (JSON) to stdout/stderr
- [ ] Prometheus metrics exposed on /metrics endpoint
- [ ] Alerts configured for key SLIs (error rate, latency, availability)
- [ ] Distributed tracing enabled

## Pre-Deployment Final

- [ ] Staging deployment matches production configuration
- [ ] Smoke test suite passes against staging
- [ ] Runbook documented for rollback procedure
- [ ] On-call team notified of deployment window

## Sign-Off

**Reviewed by:** _______________
**Cluster:** _______________
**Date:** _______________
**Approved:** [ ] Yes [ ] No
