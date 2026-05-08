from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.database import init_db, close_db
from app.db.redis import redis_client
from app.websocket.connection_manager import connection_manager

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info(
        "application_starting",
        version=settings.app_version,
        environment=settings.environment
    )

    # Connect to Redis
    await redis_client.connect()

    # Initialize database (create tables if they don't exist)
    # Note: In production, use Alembic migrations instead
    if settings.is_testing or settings.debug:
        await init_db()

    logger.info("application_started")

    yield

    # Shutdown
    logger.info("application_shutting_down")

    # Close connections
    await close_db()
    await redis_client.disconnect()

    # Disconnect all WebSocket clients
    for user_id in list(connection_manager.active_connections.keys()):
        await connection_manager.disconnect(user_id)

    logger.info("application_shutdown_complete")


def create_application() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="SafeNest - GBV Safety and Emergency Response Platform API",
        default_response_class=ORJSONResponse,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins if isinstance(settings.cors_origins, list) else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def log_operator_login_preflight_errors(request, call_next):
        response = await call_next(request)

        if (
            request.method == "OPTIONS"
            and request.url.path == "/api/v1/operator/auth/login"
            and response.status_code >= 400
        ):
            logger.warning(
                "operator_login_preflight_failed",
                status_code=response.status_code,
                origin=request.headers.get("origin"),
                requested_method=request.headers.get("access-control-request-method"),
                requested_headers=request.headers.get("access-control-request-headers"),
                allowed_origins=settings.cors_origins,
            )

        return response

    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    # Redirect /docs to /api/docs
    from fastapi.responses import RedirectResponse

    @app.get("/docs", include_in_schema=False)
    async def redirect_docs():
        return RedirectResponse(url="/api/docs")

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "docs": "/api/docs"
        }

    # Exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(
            "unhandled_exception",
            error=str(exc),
            path=request.url.path,
            method=request.method
        )
        return ORJSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        )

    return app


# Create the application instance
app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        workers=1 if settings.debug else 4
    )
