---
title: "CI/CD Pipeline Design with GitHub Actions"
type: guide
domain: devops
level: intermediate
status: active
version: v1.0
tags: [cicd, github-actions, devops, pipeline, automation]
related:
  - "[[Docker_Multi_Stage_Builds]]"
  - "[[Kubernetes_Deployment_Readiness]]"
  - "[[Backend_API_Production_Readiness]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to designing robust CI/CD pipelines with GitHub Actions — covering workflow structure, job dependencies, secrets management, caching, and deployment strategies.

## Prerequisites

- GitHub repository with code
- Basic YAML knowledge
- Target deployment environment (cloud, container registry, or server)

## Pipeline Structure

```
Push/PR → Lint → Test → Build → Security Scan → Deploy (on main)
```

## Step 1: Basic CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install flake8 mypy
      - run: flake8 src/ tests/
      - run: mypy src/

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements*.txt') }}
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=src/ --cov-report=xml
      - uses: codecov/codecov-action@v4
```

## Step 2: Docker Build and Push

```yaml
  build:
    runs-on: ubuntu-latest
    needs: test
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## Step 3: Deployment Job

```yaml
  deploy:
    runs-on: ubuntu-latest
    needs: build
    environment: production
    steps:
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/myapp \
            app=ghcr.io/${{ github.repository }}:${{ github.sha }}
        env:
          KUBECONFIG: ${{ secrets.KUBECONFIG }}
```

## Job Dependencies

```
lint ──→ test ──→ build ──→ deploy
              └──→ security-scan ──→ (blocks deploy on failure)
```

## Best Practices

### Secrets Management
- Store API keys and credentials in GitHub Secrets (repository or environment)
- Never print secrets in logs
- Use environment-level secrets for production deployments
- Rotate secrets regularly

### Caching Strategy
- Cache package managers (pip, npm, cargo)
- Cache Docker layers with `cache-from/cache-to`
- Invalidate cache on lockfile changes

### Branch Protection
- Require CI to pass before merge
- Require code review for main branch
- Enable automatic deletion of merged branches

### Matrix Testing

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
    os: [ubuntu-latest, macos-latest]
```

## Deployment Strategies

| Strategy | Downtime | Risk | Complexity |
|----------|----------|------|------------|
| Rolling update | None | Medium | Low |
| Blue/green | None | Low | Medium |
| Canary | None | Low | High |
| Recreate | Yes | High | Low |

## Conclusion

A well-designed GitHub Actions pipeline enforces code quality automatically, builds reproducible artifacts, and deploys safely. Start with lint + test + build, add security scanning, and implement environment-gated deployments for production.
