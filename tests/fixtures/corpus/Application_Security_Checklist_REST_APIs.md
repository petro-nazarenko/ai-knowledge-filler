---
title: "Application Security Checklist for REST APIs"
type: checklist
domain: security
level: intermediate
status: active
tags: [security, api, checklist, owasp, rest]
related:
  - "[[OAuth_2_Implementation]]"
  - "[[Zero_Trust_Architecture_Principles]]"
  - "[[Backend_API_Production_Readiness]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Comprehensive security review checklist for REST APIs before production deployment. Based on OWASP API Security Top 10.

## Authentication

- [ ] HTTPS enforced for all endpoints (no HTTP fallback)
- [ ] TLS 1.2+ minimum, TLS 1.3 preferred
- [ ] Strong authentication mechanism implemented (OAuth 2.0, JWT, API keys)
- [ ] Credentials never passed in URL query parameters
- [ ] Token expiration implemented (15–60 minutes for access tokens)
- [ ] Refresh token rotation enabled
- [ ] Multi-factor authentication for admin endpoints

## Authorization

- [ ] Broken Object Level Authorization (BOLA) prevented
- [ ] Users can only access their own resources
- [ ] Role-based access control (RBAC) enforced
- [ ] Function-level authorization checked (not just route-level)
- [ ] Privilege escalation prevented
- [ ] Admin endpoints require elevated role + MFA

## Input Validation

- [ ] All inputs validated against allowlist (not blocklist)
- [ ] Input length limits enforced
- [ ] SQL injection prevented (parameterized queries, ORM)
- [ ] NoSQL injection prevented
- [ ] XML/JSON injection prevented
- [ ] File upload type and size restricted
- [ ] Content-Type validated against expected type

## Output and Data Exposure

- [ ] Response schema minimized (no excess data)
- [ ] Sensitive fields (passwords, tokens) never returned
- [ ] PII handled per data classification policy
- [ ] Stack traces not exposed in error responses
- [ ] Internal service URLs not exposed

## Rate Limiting and DoS Protection

- [ ] Rate limiting implemented per endpoint and per user
- [ ] 429 Too Many Requests returned on limit exceeded
- [ ] Request size limits enforced (body, headers)
- [ ] Query complexity limits for GraphQL APIs
- [ ] Timeout values set on all endpoints

## Security Headers

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'none'
Referrer-Policy: no-referrer
```

- [ ] All security headers present on all responses
- [ ] CORS policy is restrictive (not wildcard `*` for authenticated endpoints)

## Cryptography

- [ ] No custom cryptographic implementations
- [ ] Secrets stored encrypted (not plaintext)
- [ ] JWT signed with RS256 or ES256 (not HS256 in distributed systems)
- [ ] Sensitive data encrypted at rest
- [ ] API keys hashed in storage (not stored plaintext)

## Logging and Monitoring

- [ ] All authentication events logged (success and failure)
- [ ] Authorization failures logged
- [ ] Sensitive data excluded from logs
- [ ] Log injection prevented (input sanitized before logging)
- [ ] Alerting on unusual patterns (failed logins, access spikes)

## Dependencies

- [ ] All dependencies scanned for CVEs
- [ ] Dependency versions pinned
- [ ] Automated vulnerability scanning in CI/CD

## Sign-Off

**Security Reviewer:** _______________
**Date:** _______________
**OWASP Top 10 Coverage:** [ ] Complete [ ] Partial
**Approved:** [ ] Yes [ ] No
