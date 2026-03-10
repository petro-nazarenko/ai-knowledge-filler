---
title: "Docker Multi-Stage Builds for Production Optimization"
type: reference
domain: devops
level: intermediate
status: active
version: v1.0
tags: [docker, multi-stage-builds, containerization, optimization, production]
related:
  - "[[CICD_Pipeline_Design_GitHub_Actions]]"
  - "[[Kubernetes_Deployment_Readiness]]"
  - "[[Backend_API_Production_Readiness]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Reference for Docker multi-stage build patterns — techniques for producing minimal, secure production images by separating build and runtime environments.

## Core Concept

Multi-stage builds use multiple `FROM` instructions in a single Dockerfile. Each stage has a name and can copy artifacts from previous stages. Only the final stage becomes the image.

## Basic Pattern

```dockerfile
# Stage 1: Build
FROM node:20 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Runtime (only final stage ships)
FROM node:20-alpine AS runtime
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

**Result:** Build stage (~1.2GB) discarded. Runtime image ~180MB.

## Language-Specific Patterns

### Python FastAPI

```dockerfile
FROM python:3.12 AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY ./src ./src
ENV PATH=/root/.local/bin:$PATH
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Go Binary

```dockerfile
FROM golang:1.22 AS builder
WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o server ./cmd/server

FROM scratch AS runtime
COPY --from=builder /build/server /server
EXPOSE 8080
ENTRYPOINT ["/server"]
```

**Scratch image:** ~10MB total. Only the static binary.

## Optimization Techniques

### Layer Caching

Order instructions from least to most frequently changed:

```dockerfile
# Good: dependencies cached separately from source
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ./src .  # Source changes don't invalidate pip cache

# Bad: source copied before dependency install
COPY . .
RUN pip install -r requirements.txt  # Cache busted on any file change
```

### .dockerignore

```
.git
.github
__pycache__
*.pyc
tests/
docs/
*.md
.env
node_modules/
dist/
```

### BuildKit Cache Mounts

```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

## Image Size Comparison

| Base Image | Size |
|-----------|------|
| ubuntu | ~80MB |
| debian | ~45MB |
| python:3.12 | ~350MB |
| python:3.12-slim | ~130MB |
| python:3.12-alpine | ~55MB |
| scratch | 0MB |

## Security Hardening

```dockerfile
# Run as non-root
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Read-only filesystem
RUN chmod -R 755 /app

# No shell in final image (optional — prevents shell injection)
FROM scratch
COPY --from=builder /app/server /server
ENTRYPOINT ["/server"]
```

## Conclusion

Multi-stage builds are non-negotiable for production Docker images. Separate build tools from runtime, cache dependencies correctly, and use minimal base images. A well-optimized image is faster to pull, cheaper to store, and has a smaller attack surface.
