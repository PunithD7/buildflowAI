"""
Rate Limiting Middleware - Per-user, per-agent, token budget management
"""
import logging
import time
from typing import Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """Token bucket rate limiter with abuse prevention."""
    
    def __init__(self):
        # {key: {"count": int, "window_start": float, "blocked_until": float}}
        self._buckets: Dict[str, Dict] = {}
        self._abuse_tracker: Dict[str, int] = {}
    
    def _get_or_create_bucket(self, key: str, window_seconds: int = 60) -> Dict:
        now = time.time()
        if key not in self._buckets:
            self._buckets[key] = {
                "count": 0,
                "window_start": now,
                "blocked_until": 0,
                "violations": 0,
            }
        bucket = self._buckets[key]
        # Reset window if expired
        if now - bucket["window_start"] >= window_seconds:
            bucket["count"] = 0
            bucket["window_start"] = now
        return bucket
    
    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60
    ) -> tuple[bool, Dict]:
        """
        Returns (allowed, info_dict).
        info_dict has: remaining, reset_at, blocked_until
        """
        now = time.time()
        bucket = self._get_or_create_bucket(key, window_seconds)
        
        # Check if blocked
        if bucket["blocked_until"] > now:
            return False, {
                "remaining": 0,
                "reset_at": bucket["blocked_until"],
                "blocked": True,
                "retry_after": int(bucket["blocked_until"] - now),
            }
        
        bucket["count"] += 1
        
        if bucket["count"] > limit:
            bucket["violations"] += 1
            # Progressive blocking: 1min, 5min, 30min, 1hr
            block_durations = [60, 300, 1800, 3600]
            block_duration = block_durations[min(bucket["violations"] - 1, len(block_durations) - 1)]
            bucket["blocked_until"] = now + block_duration
            
            logger.warning(
                f"[Rate Limiter] 🚫 Key={key} blocked for {block_duration}s "
                f"(violation #{bucket['violations']})"
            )
            
            return False, {
                "remaining": 0,
                "reset_at": bucket["blocked_until"],
                "blocked": True,
                "retry_after": block_duration,
                "violations": bucket["violations"],
            }
        
        remaining = max(0, limit - bucket["count"])
        return True, {
            "remaining": remaining,
            "reset_at": bucket["window_start"] + window_seconds,
            "blocked": False,
        }
    
    def cleanup_old_entries(self, max_age_seconds: int = 3600):
        """Clean up stale rate limit buckets."""
        now = time.time()
        to_delete = [
            key for key, bucket in self._buckets.items()
            if now - bucket["window_start"] > max_age_seconds
        ]
        for key in to_delete:
            del self._buckets[key]


# Global rate limiter instance
_rate_limiter = InMemoryRateLimiter()


def get_client_identifier(request: Request) -> str:
    """Extract client identifier for rate limiting."""
    # Check for authenticated user
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    
    # Fall back to IP address
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return f"ip:{forwarded_for.split(',')[0].strip()}"
    
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with per-user and burst protection."""
    
    # Paths exempt from rate limiting
    EXEMPT_PATHS = {"/health", "/", "/api/v1/status", "/api/docs", "/api/redoc", "/api/openapi.json"}
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        client_id = get_client_identifier(request)
        
        # Per-minute rate limit
        allowed, info = _rate_limiter.check_rate_limit(
            key=f"rate:{client_id}:minute",
            limit=settings.RATE_LIMIT_PER_MINUTE,
            window_seconds=60,
        )
        
        if not allowed:
            # Send security event
            try:
                from app.core.websocket_manager import ws_manager
                await ws_manager.send_security_event("rate_limit_exceeded", {
                    "client_id": client_id,
                    "path": request.url.path,
                    "retry_after": info.get("retry_after"),
                })
            except Exception:
                pass
            
            logger.warning(f"[Rate Limiter] Request throttled: {client_id} -> {request.url.path}")
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": info.get("retry_after"),
                    "reset_at": info.get("reset_at"),
                },
                headers={
                    "Retry-After": str(info.get("retry_after", 60)),
                    "X-Rate-Limit-Remaining": "0",
                    "X-Rate-Limit-Reset": str(int(info.get("reset_at", 0))),
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-Rate-Limit-Remaining"] = str(info.get("remaining", 0))
        response.headers["X-Rate-Limit-Reset"] = str(int(info.get("reset_at", 0)))
        response.headers["X-Rate-Limit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
        
        return response


def get_rate_limiter() -> InMemoryRateLimiter:
    """Get the global rate limiter instance."""
    return _rate_limiter
