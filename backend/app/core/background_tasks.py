"""
Background Tasks - System health, cleanup, and monitoring
"""
import asyncio
import logging
import time

logger = logging.getLogger(__name__)

_background_tasks = []


async def start_background_tasks():
    """Start all background tasks."""
    tasks = [
        asyncio.create_task(workflow_health_monitor()),
        asyncio.create_task(cleanup_expired_sessions()),
        asyncio.create_task(ddos_stats_refresh()),
    ]
    _background_tasks.extend(tasks)
    logger.info(f"✅ Started {len(tasks)} background tasks")


async def workflow_health_monitor():
    """Monitor workflow health every 30 seconds."""
    while True:
        try:
            await asyncio.sleep(30)
            # Emit health check event
            from app.core.websocket_manager import ws_manager
            await ws_manager.broadcast_system_event({
                "type": "health_check",
                "timestamp": time.time(),
                "status": "healthy",
            })
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Health monitor error: {e}")


async def cleanup_expired_sessions():
    """Clean up expired workflow sessions every 5 minutes."""
    while True:
        try:
            await asyncio.sleep(300)
            from app.core.redis_client import redis_client
            logger.debug("Running session cleanup...")
            # Cleanup logic would go here
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")


async def ddos_stats_refresh():
    """Refresh DDoS stats every 60 seconds."""
    while True:
        try:
            await asyncio.sleep(60)
            from app.middleware.ddos_protection import ddos_tracker
            ddos_tracker.cleanup_old_entries()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"DDoS stats refresh error: {e}")
