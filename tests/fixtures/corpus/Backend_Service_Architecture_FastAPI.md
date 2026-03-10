---
title: "Backend Service Architecture with FastAPI and Async Python"
type: reference
domain: backend-engineering
level: intermediate
status: active
version: v1.0
tags: [fastapi, async, python, backend, architecture]
related:
  - "[[API_Rate_Limiting_with_FastAPI]]"
  - "[[Python_Packaging_Best_Practices]]"
  - "[[Backend_API_Production_Readiness]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Reference architecture for production backend services using FastAPI and async Python — covering project structure, dependency injection, async patterns, database access, and deployment.

## Project Structure

```
src/
├── api/
│   ├── __init__.py
│   ├── routers/
│   │   ├── orders.py
│   │   └── users.py
│   └── dependencies.py
├── core/
│   ├── config.py
│   └── security.py
├── models/
│   ├── domain.py      # Pydantic domain models
│   └── schemas.py     # API request/response schemas
├── services/
│   ├── orders.py
│   └── users.py
├── repositories/
│   ├── orders.py
│   └── base.py
├── db.py              # Database connection
└── main.py
```

## Application Factory

```python
# src/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from api.routers import orders, users
from db import init_db, close_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

def create_app() -> FastAPI:
    app = FastAPI(
        title="My Service",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
    return app

app = create_app()
```

## Dependency Injection

```python
# api/dependencies.py
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from services.orders import OrderService

async def get_order_service(
    db: AsyncSession = Depends(get_session),
) -> OrderService:
    return OrderService(db)

# Router usage
@router.get("/{order_id}")
async def get_order(
    order_id: str,
    service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_user),
):
    return await service.get(order_id, user_id=current_user.id)
```

## Async Database Access (SQLAlchemy 2.0)

```python
# db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    pool_size=20,
    max_overflow=0,
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

## Repository Pattern

```python
# repositories/base.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class BaseRepository[T]:
    def __init__(self, session: AsyncSession, model: type[T]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: str) -> T | None:
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def save(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
```

## Configuration Management

```python
# core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    api_key: str
    debug: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

## Error Handling

```python
# Global exception handler
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "type": "validation_error"},
    )
```

## Performance Checklist

- [ ] Async database driver (asyncpg, aiosqlite)
- [ ] Connection pooling configured
- [ ] Background tasks for non-critical operations
- [ ] Response caching for read-heavy endpoints
- [ ] Pagination on all list endpoints
- [ ] Database query optimization (avoid N+1)

## Conclusion

FastAPI with async Python provides excellent performance through event loop concurrency. Separate concerns with dependency injection, use the repository pattern for data access, and configure async database drivers. The project structure above scales from small services to team-scale codebases.
