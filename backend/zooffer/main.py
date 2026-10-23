from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.gzip import GZipMiddleware

from zooffer.api import system
from zooffer.api.deps import check_origin
from zooffer.api.v1 import account as account_api
from zooffer.api.v1 import admin as admin_api
from zooffer.api.v1 import animals as animals_api
from zooffer.api.v1 import auth as auth_api
from zooffer.api.v1 import billing as billing_api
from zooffer.api.v1 import discovery as discovery_api
from zooffer.api.v1 import listings as listings_api
from zooffer.api.v1 import media as media_api
from zooffer.api.v1 import messaging as messaging_api
from zooffer.api.v1 import notifications as notifications_api
from zooffer.api.v1 import reports as reports_api
from zooffer.config import settings
from zooffer.core.errors import AppError, app_error_handler
from zooffer.core.logging import configure_logging, get_logger
from zooffer.core.middleware import RequestContextMiddleware
from zooffer.db.session import dispose_engine

logger = get_logger("zooffer.app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level)
    logger.info("startup", environment=settings.environment)
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Zooffer API",
        version="0.1.0",
        description="Zooffer — animal discovery and marketplace platform API",
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.app_base_url, settings.api_base_url],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", settings.csrf_header, "X-Request-ID"],
        max_age=600,
    )
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error.get("loc", []) if part != "body")
            details.append(
                {"field": location, "message": error.get("msg", "Некорректное значение")}
            )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Проверьте заполненные поля",
                    "details": details,
                    "correlation_id": getattr(request.state, "correlation_id", None),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Что-то пошло не так. Попробуйте ещё раз.",
                    "correlation_id": getattr(request.state, "correlation_id", None),
                }
            },
        )

    @app.middleware("http")
    async def origin_guard(request: Request, call_next):  # type: ignore[no-untyped-def]
        check_origin(request)
        return await call_next(request)

    app.include_router(system.router)
    # Media is served from a stable, CDN-friendly root path; the /api/v1 alias keeps
    # older clients and tests working.
    app.include_router(media_api.router)
    app.include_router(media_api.router, prefix="/api/v1")
    app.include_router(auth_api.router, prefix="/api/v1")
    app.include_router(animals_api.router, prefix="/api/v1")
    app.include_router(listings_api.router, prefix="/api/v1")
    app.include_router(listings_api.public_router, prefix="/api/v1")
    app.include_router(discovery_api.router, prefix="/api/v1")
    app.include_router(discovery_api.favorites_router, prefix="/api/v1")
    app.include_router(messaging_api.router, prefix="/api/v1")
    app.include_router(notifications_api.router, prefix="/api/v1")
    app.include_router(billing_api.router, prefix="/api/v1")
    app.include_router(account_api.router, prefix="/api/v1")
    app.include_router(account_api.public_router, prefix="/api/v1")
    app.include_router(reports_api.router, prefix="/api/v1")
    app.include_router(admin_api.router, prefix="/api/v1")
    app.include_router(account_api.click_router)
    return app


app = create_app()
