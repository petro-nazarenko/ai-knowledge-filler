---
title: "API Documentation Structure with OpenAPI Spec"
type: reference
domain: api-design
level: intermediate
status: active
version: v1.0
tags: [openapi, api-documentation, swagger, rest, api-design]
related:
  - "[[REST_API_Versioning_Strategies]]"
  - "[[Technical_Documentation_Standards]]"
  - "[[Backend_Service_Architecture_FastAPI]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Reference for structuring API documentation using the OpenAPI 3.1 specification — covering info, paths, components, schemas, and security definitions.

## OpenAPI Document Structure

```yaml
openapi: "3.1.0"
info:
  title: My API
  version: "1.0.0"
  description: |
    Full API description. Supports Markdown.
  contact:
    email: api-support@example.com
  license:
    name: MIT

servers:
  - url: https://api.example.com/v1
    description: Production
  - url: https://api-staging.example.com/v1
    description: Staging

tags:
  - name: orders
    description: Order management operations
  - name: users
    description: User management operations

paths:
  /orders/{order_id}:
    get:
      tags: [orders]
      summary: Get order by ID
      operationId: getOrder
      parameters:
        - $ref: '#/components/parameters/OrderId'
      responses:
        "200":
          description: Order found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Order'
        "404":
          $ref: '#/components/responses/NotFound'
      security:
        - BearerAuth: []

components:
  schemas:
    Order:
      type: object
      required: [id, status, created_at]
      properties:
        id:
          type: string
          format: uuid
          example: "550e8400-e29b-41d4-a716-446655440000"
        status:
          type: string
          enum: [pending, confirmed, shipped, delivered, cancelled]
        created_at:
          type: string
          format: date-time

    Error:
      type: object
      required: [detail, type]
      properties:
        detail:
          type: string
        type:
          type: string

  parameters:
    OrderId:
      name: order_id
      in: path
      required: true
      schema:
        type: string
        format: uuid

  responses:
    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

## FastAPI Auto-Generation

FastAPI generates OpenAPI spec automatically from type annotations:

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="My API",
    version="1.0.0",
    description="API description",
)

class Order(BaseModel):
    id: str
    status: Literal["pending", "confirmed", "shipped"]
    created_at: datetime

@app.get(
    "/orders/{order_id}",
    response_model=Order,
    summary="Get order by ID",
    responses={404: {"model": ErrorResponse}},
)
async def get_order(order_id: str) -> Order:
    """Get a single order by its ID."""
    ...
```

Access at `/docs` (Swagger UI) and `/redoc` (ReDoc).

## Documentation Best Practices

### Descriptions
- `summary`: One sentence (shown in list)
- `description`: Full explanation with examples (shown in detail)
- Include `example` values for all fields

### Versioning
- Include version in `info.version`
- Use `/v1`, `/v2` server URL prefix
- Document breaking changes in description

### Examples

```yaml
content:
  application/json:
    examples:
      new_order:
        summary: New order example
        value:
          product_id: "prod-123"
          quantity: 2
      bulk_order:
        summary: Bulk order example
        value:
          product_id: "prod-456"
          quantity: 100
```

## Tooling

| Tool | Purpose |
|------|---------|
| Swagger UI | Interactive API explorer |
| ReDoc | Clean documentation site |
| Stoplight | API design platform |
| Postman | API testing + documentation |
| spectral | OpenAPI linting |

## Conclusion

OpenAPI spec is both documentation and contract. FastAPI generates it automatically from code — keep it accurate by using response_model and proper type annotations. Publish Swagger UI in staging; restrict or hide in production for public-facing APIs.
