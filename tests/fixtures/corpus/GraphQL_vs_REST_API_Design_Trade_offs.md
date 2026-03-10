---
title: "GraphQL vs REST API Design Trade-offs"
type: concept
domain: api-design
level: intermediate
status: active
tags: [graphql, rest, api-design, trade-offs, architecture]
related:
  - "[[REST_API_Versioning_Strategies]]"
  - "[[API_Documentation_Structure_OpenAPI]]"
  - "[[Backend_Service_Architecture_FastAPI]]"
created: 2026-03-10
updated: 2026-03-10
---

## Overview

GraphQL and REST are two dominant paradigms for API design. This document covers their structural differences, performance characteristics, and practical trade-offs to inform architectural decisions.

## Core Differences

| Dimension | REST | GraphQL |
|-----------|------|---------|
| Data fetching | Multiple endpoints | Single endpoint |
| Response shape | Fixed by server | Defined by client |
| Versioning | URL or header | Schema evolution |
| Caching | HTTP native | Client-side only |
| Error handling | HTTP status codes | Always 200, errors in body |
| Tooling | Universal | GraphQL-specific |
| Learning curve | Low | Medium-High |

## REST Strengths

### Simplicity and Familiarity
REST maps directly to HTTP semantics (GET, POST, PUT, DELETE). Every developer and tool understands it.

### HTTP Caching
GET responses are cacheable by CDNs and proxies without additional configuration. GraphQL POST requests are not.

### Standardized Error Handling
HTTP status codes (400, 401, 403, 404, 429, 500) are universally understood by clients, proxies, and monitoring tools.

### Stateless by Design
Each request contains all necessary context. No session state on the server.

## GraphQL Strengths

### No Over-fetching
Clients request exactly the fields they need. Mobile clients avoid downloading large payloads.

### No Under-fetching
A single query can retrieve nested related data that would require multiple REST requests.

### Strongly Typed Schema
The schema is both documentation and contract. Type mismatches are caught at query validation time.

### Schema Introspection
Clients can query the schema itself, enabling powerful tooling (GraphiQL, Apollo Studio).

## When to Choose REST

- Public APIs consumed by unknown third parties
- Simple CRUD operations with predictable data shapes
- Heavy CDN caching requirements
- Teams with limited GraphQL experience
- Microservices with well-defined bounded contexts

## When to Choose GraphQL

- Multiple client types (web, mobile, third-party) with different data needs
- Complex nested data relationships
- Rapidly evolving frontend requirements
- Teams building internal APIs with tight frontend-backend coupling

## Performance Considerations

### N+1 Problem (GraphQL)
GraphQL resolvers can trigger N+1 database queries. Mitigation: DataLoader pattern for batching.

### Over-fetching (REST)
REST endpoints may return more data than needed. Mitigation: sparse fieldsets, custom endpoints.

### Query Complexity (GraphQL)
Clients can craft deeply nested queries that overwhelm the server. Mitigation: query depth limits, complexity scoring.

## Conclusion

REST is the right default for public APIs and simple CRUD services. GraphQL shines in product APIs where multiple client types need different data shapes from the same backend. Most large applications benefit from REST for external APIs and GraphQL for internal product APIs.
