"""
DDoS Protection Middleware - Traffic flood detection & mitigation
"""
import logging
import time
from collections import defaultdict, deque
from typing import Dict, Deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


class DDoSTracker:
    """Tracks per-IP request rates to detect DDoS-like floods."""
    
    def __init__(self):
        # {ip: deque of timestamps in current window}
        self._request_windows: Dict[str, Deque[float]] = defaultdict(lambda: deque())
        # {ip: banned_until timestamp}
        self._banned_ips: Dict[str, float] = {}
        # {ip: ban_count}
        self._ban_counts: Dict[str, int] = defaultdict(int)
        # Suspicious IPs that triggered alerts
        self._suspicious_ips: set = set()
        # Global stats
        self.total_blocked = 0
        self.total_alerts = 0
    
    def is_banned(self, ip: str) -> tuple[bool, float]:
        """Check if IP is currently banned."""
        if ip in self._banned_ips:
            if time.time() < self._banned_ips[ip]:
                return True, self._banned_ips[ip]
            else:
                # Ban expired
                del self._banned_ips[ip]
        return False, 0
    
    def record_request(self, ip: str) -> tuple[bool, str]:
        """
        Record a request and check for DDoS patterns.
        Returns (allowed, reason).
        """
        # Skip whitelisted IPs
        if ip in settings.DDOS_WHITELIST:
            return True, ""
        
        # Check ban status
        banned, until = self.is_banned(ip)
        if banned:
            self.total_blocked += 1
            return False, f"IP banned until {time.strftime('%H:%M:%S', time.localtime(until))}"
        
        now = time.time()
        window = self._request_windows[ip]
        
        # Clean entries older than 1 second
        while window and now - window[0] > 1.0:
            window.popleft()
        
        window.append(now)
        
        # Check threshold
        if len(window) > settings.DDOS_THRESHOLD_PER_SECOND:
            self._ban_ip(ip)
            self.total_alerts += 1
            logger.warning(
                f"[DDoS Protection] 🚨 Attack detected from {ip}: "
                f"{len(window)} req/s (threshold: {settings.DDOS_THRESHOLD_PER_SECOND})"
            )
            return False, f"DDoS pattern detected: {len(window)} requests/second"
        
        # Check for suspicious activity (>50% of threshold)
        warning_threshold = settings.DDOS_THRESHOLD_PER_SECOND * 0.5
        if len(window) > warning_threshold and ip not in self._suspicious_ips:
            self._suspicious_ips.add(ip)
            logger.warning(f"[DDoS Protection] ⚠️  Suspicious traffic from {ip}: {len(window)} req/s")
        
        return True, ""
    
    def _ban_ip(self, ip: str):
        """Ban an IP address."""
        self._ban_counts[ip] += 1
        # Escalating ban durations
        ban_count = self._ban_counts[ip]
        duration = min(
            settings.DDOS_BAN_DURATION_SECONDS * ban_count,
            86400  # Max 24 hours
        )
        self._banned_ips[ip] = time.time() + duration
        self.total_blocked += 1
        logger.error(
            f"[DDoS Protection] 🚫 IP {ip} banned for {duration}s "
            f"(ban #{ban_count})"
        )
    
    def simulate_attack(self, attacker_ip: str = "192.168.1.100", requests: int = 200):
        """Simulate a DDoS attack for demonstration."""
        logger.warning(f"[DDoS SIMULATION] 🧪 Simulating attack from {attacker_ip}")
        for _ in range(requests):
            self._request_windows[attacker_ip].append(time.time())
        self._ban_ip(attacker_ip)
        return {
            "attacker_ip": attacker_ip,
            "requests_simulated": requests,
            "status": "ip_banned",
            "ban_duration": settings.DDOS_BAN_DURATION_SECONDS,
        }
    
    def unban_ip(self, ip: str) -> bool:
        """Unban an IP (admin action)."""
        if ip in self._banned_ips:
            del self._banned_ips[ip]
            logger.info(f"[DDoS Protection] ✅ IP {ip} unbanned by admin")
            return True
        return False
    
    def get_stats(self) -> dict:
        """Get DDoS protection statistics."""
        return {
            "active_bans": len(self._banned_ips),
            "banned_ips": list(self._banned_ips.keys()),
            "suspicious_ips": list(self._suspicious_ips),
            "total_blocked": self.total_blocked,
            "total_alerts": self.total_alerts,
            "threshold_per_second": settings.DDOS_THRESHOLD_PER_SECOND,
            "whitelist": settings.DDOS_WHITELIST,
        }
    
    def cleanup_old_entries(self):
        """Remove stale tracking data."""
        now = time.time()
        # Clear old windows
        to_delete = [
            ip for ip, window in self._request_windows.items()
            if not window or now - max(window) > 300
        ]
        for ip in to_delete:
            del self._request_windows[ip]
        # Clear expired bans
        expired_bans = [ip for ip, until in self._banned_ips.items() if now > until]
        for ip in expired_bans:
            del self._banned_ips[ip]


# Global tracker instance
ddos_tracker = DDoSTracker()


class DDoSProtectionMiddleware(BaseHTTPMiddleware):
    """DDoS protection middleware."""
    
    EXEMPT_PATHS = {"/health", "/"}
    
    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        allowed, reason = ddos_tracker.record_request(client_ip)
        
        if not allowed:
            # Send security alert via WebSocket
            try:
                from app.core.websocket_manager import ws_manager
                await ws_manager.send_security_event("ddos_blocked", {
                    "ip": client_ip,
                    "reason": reason,
                    "path": request.url.path,
                })
            except Exception:
                pass
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "ddos_protection_active",
                    "message": "Request blocked by DDoS protection",
                    "reason": reason,
                },
                headers={
                    "Retry-After": str(settings.DDOS_BAN_DURATION_SECONDS),
                    "X-Blocked-By": "DDoS-Protection",
                }
            )
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"
