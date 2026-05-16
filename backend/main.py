"""
BuildFlow Secure AI - Main FastAPI Application
Secure Autonomous Digital Execution Platform
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.redis_client import redis_client
from app.api.v1.router import api_router
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.ddos_protection import DDoSProtectionMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.api.v1.endpoints import websocket as websocket_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    logger.info("🚀 BuildFlow Secure AI starting up...")
    
    # Initialize Redis connection
    try:
        await redis_client.initialize()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.warning(f"⚠️  Redis not available: {e}. Running without Redis.")
    
    # Initialize background tasks
    from app.core.background_tasks import start_background_tasks
    await start_background_tasks()
    logger.info("✅ Background tasks initialized")
    
    logger.info("🎯 BuildFlow Secure AI is ready!")
    
    yield
    
    # Cleanup
    logger.info("🛑 BuildFlow Secure AI shutting down...")
    await redis_client.close()
    logger.info("✅ Cleanup complete")


# Create FastAPI application
app = FastAPI(
    title="BuildFlow Secure AI",
    description="Secure Autonomous Digital Execution Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ============================================================
# MIDDLEWARE STACK (Order matters - outermost first)
# ============================================================

# Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# DDoS Protection
app.add_middleware(DDoSProtectionMiddleware)

# Rate Limiting
app.add_middleware(RateLimitMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Rate-Limit-Remaining", "X-Rate-Limit-Reset"],
)

# Trusted Hosts
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )


# ============================================================
# GLOBAL EXCEPTION HANDLERS
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", None),
        }
    )


# ============================================================
# REQUEST TRACKING MIDDLEWARE
# ============================================================

@app.middleware("http")
async def request_tracking_middleware(request: Request, call_next):
    """Add request ID and track timing."""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    
    logger.info(
        f"[{request.method}] {request.url.path} "
        f"status={response.status_code} "
        f"duration={duration:.3f}s "
        f"request_id={request_id}"
    )
    
    return response


# ============================================================
# ROUTES
# ============================================================

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Include WebSocket router at root level
app.include_router(websocket_router.router, tags=["WebSocket"])


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint."""
    return {
        "name": "BuildFlow Secure AI",
        "version": "1.0.0",
        "status": "operational",
        "description": "Secure Autonomous Digital Execution Platform",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """System health check."""
    redis_status = "connected" if await redis_client.ping() else "disconnected"
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "api": "operational",
            "redis": redis_status,
            "agents": "ready",
        }
    }


@app.get("/api/v1/status", tags=["Status"])
async def system_status():
    """Detailed system status."""
    return {
        "platform": "BuildFlow Secure AI",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "agents": {
            "total": 13,
            "active": 0,
            "available": 13,
        },
        "security": {
            "rate_limiting": "active",
            "ddos_protection": "active",
            "tee_execution": "active",
            "rbac": "active",
        },
        "observability": {
            "logging": "active",
            "metrics": "active",
            "tracing": "active",
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="info",
        workers=1 if settings.ENVIRONMENT == "development" else 4,
    )
