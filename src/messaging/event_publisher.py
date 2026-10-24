import json
import logging
import asyncio
from datetime import datetime
from config.settings import Settings

logger = logging.getLogger(__name__)

class EventPublisher:
    def __init__(self, settings: Settings, nc, vps_id: str):
        self._settings = settings
        self._nc = nc
        self._vps_id = vps_id

    async def publish_heartbeat(self, worker_id: str, status: str, active_contexts: int = 0):
        subject = f"worker.heartbeat.{self._vps_id}.redjum"
        payload = {
            "workerId": worker_id,
            "vpsId": self._vps_id,
            "entity": "redjum",
            "status": status,
            "activeContexts": active_contexts,
            "technology": self._settings.worker_technology,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await self._nc.publish(subject, json.dumps(payload).encode("utf-8"))

    async def publish_event(self, worker_id: str, event_type: str, detail: dict, correlation_id: str = None):
        subject = f"worker.event.{self._vps_id}.redjum"
        payload = {
            "workerId": worker_id,
            "vpsId": self._vps_id,
            "entity": "redjum",
            "correlationId": correlation_id,
            "eventType": event_type,
            "detail": detail,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await self._nc.publish(subject, json.dumps(payload).encode("utf-8"))

    async def start_heartbeat_loop(self, worker_id: str, get_active_contexts_fn):
        while True:
            try:
                active_contexts = get_active_contexts_fn()
                await self.publish_heartbeat(worker_id, "active", active_contexts)
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
            await asyncio.sleep(self._settings.heartbeat_interval_seconds)
