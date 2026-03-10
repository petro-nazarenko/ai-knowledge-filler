---
title: "Zero-Trust Architecture Principles"
type: concept
domain: security
level: advanced
status: active
tags: [zero-trust, security, architecture, identity, principles]
related:
  - "[[OAuth_2_Implementation_for_API_Authentication]]"
  - "[[Application_Security_Checklist_REST_APIs]]"
  - "[[Microservices_Architecture_Patterns]]"
created: 2026-03-10
updated: 2026-03-10
---

## Overview

Zero-trust architecture (ZTA) is a security model based on the principle "never trust, always verify." It assumes breaches are inevitable and requires continuous authentication and authorization for every request, regardless of network location.

## Core Principles

### 1. Verify Explicitly
Always authenticate and authorize based on all available data points: identity, location, device health, service/workload, data classification, and anomalies.

### 2. Use Least-Privilege Access
Limit user access to only the resources required for the current task. Use just-in-time (JIT) and just-enough-access (JEA) policies.

### 3. Assume Breach
Minimize blast radius. Segment access. Verify end-to-end encryption. Use analytics to detect anomalies and get visibility.

## Traditional vs Zero-Trust

| Dimension | Traditional (Castle-and-Moat) | Zero-Trust |
|-----------|------------------------------|------------|
| Trust model | Trust the network | Trust nothing |
| Perimeter | Network boundary | Identity |
| Internal traffic | Implicitly trusted | Verified |
| Lateral movement | Easy after perimeter breach | Blocked by microsegmentation |
| VPN | Required for remote access | Not sufficient |

## Pillars of Zero-Trust

### Identity
- Strong authentication (MFA) for all users
- Service identities for all workloads (mTLS, SPIFFE/SPIRE)
- Continuous session validation

### Devices
- Device health verified before granting access
- Endpoint detection and response (EDR)
- Certificate-based device authentication

### Networks
- Microsegmentation — isolate workloads at network level
- Software-defined perimeter (SDP)
- Encrypt all traffic (mTLS between services)

### Applications
- Application-level access control
- API gateway as enforcement point
- OAuth 2.0 + PKCE for user access

### Data
- Data classification and labeling
- Encryption at rest and in transit
- Data loss prevention (DLP)

## Implementation Path

### Phase 1: Identity Foundation
- Deploy identity provider (IdP)
- Enforce MFA for all users
- Implement SSO with OAuth 2.0

### Phase 2: Device Trust
- Enroll devices in MDM
- Require device compliance for access
- Deploy certificate-based authentication

### Phase 3: Network Segmentation
- Implement microsegmentation
- Replace VPN with zero-trust network access (ZTNA)
- Enable mTLS between services

### Phase 4: Application and Data Controls
- API gateway authorization
- Data classification
- Continuous monitoring and analytics

## Service Mesh Integration

Service mesh (Istio, Linkerd) implements zero-trust at the infrastructure level:
- Automatic mTLS between services
- Policy-based authorization
- Traffic encryption without application changes

```yaml
# Istio Authorization Policy
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: orders-policy
spec:
  selector:
    matchLabels:
      app: orders-service
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/payment-service"]
    to:
    - operation:
        methods: ["GET"]
        paths: ["/orders/*"]
```

## Benefits

- **Reduced blast radius** from compromised credentials
- **Lateral movement prevention** via microsegmentation
- **Compliance support** — auditable access decisions
- **Cloud-native** — works across hybrid and multi-cloud

## Conclusion

Zero-trust is not a product but an architectural philosophy. Implement incrementally, starting with strong identity verification and MFA. Full zero-trust is a multi-year journey — prioritize by risk reduction per effort.
