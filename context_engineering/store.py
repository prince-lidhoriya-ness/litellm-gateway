"""Where masked observations and compacted turns are kept, so they can be recovered by their ref.

    memory  per-worker LRU with a TTL (default): no new infrastructure; refs survive while the worker lives
    redis   the Redis the LiteLLM stack already runs (REDIS_HOST / REDIS_PORT / REDIS_PASSWORD, or
            CONTEXT_STORE_REDIS_URL), keys "ce:<ref>" with a TTL; shared by all workers, readable by recover.py.
            Content with a deterministic sensitivity hit is not written unless CONTEXT_STORE_ALLOW_SENSITIVE=true.
    none    nothing is stored

Correctness never depends on the store: the client keeps the full history and re-sends it with every request, and the
ref names the original message, so a lost entry costs only the convenience of recovery. Writes never raise.
"""

import json
import logging
import os
import threading
import time
from collections import OrderedDict
from typing import Optional

from context_engineering.settings import ContextSettings

logger = logging.getLogger("context_engineering.store")
KEY_PREFIX = "ce:"


class NullStore:
    backend = "none"

    def put(self, ref: str, payload: dict, sensitive: bool = False) -> bool:
        return False

    def get(self, ref: str) -> Optional[dict]:
        return None


class MemoryStore:
    backend = "memory"

    def __init__(self, max_items: int = 2048, ttl_s: int = 3600):
        self.max_items = max(1, max_items)
        self.ttl_s = ttl_s
        self._data: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def put(self, ref: str, payload: dict, sensitive: bool = False) -> bool:
        expires = time.monotonic() + self.ttl_s if self.ttl_s > 0 else None
        with self._lock:
            self._data[ref] = (expires, payload)
            self._data.move_to_end(ref)
            while len(self._data) > self.max_items:
                self._data.popitem(last=False)
        return True

    def get(self, ref: str) -> Optional[dict]:
        with self._lock:
            entry = self._data.get(ref)
            if entry is None:
                return None
            expires, payload = entry
            if expires is not None and expires < time.monotonic():
                del self._data[ref]
                return None
            return payload


class RedisStore:
    backend = "redis"

    def __init__(self, client, ttl_s: int = 3600, allow_sensitive: bool = False):
        self.client = client
        self.ttl_s = ttl_s
        self.allow_sensitive = allow_sensitive
        self.errors = 0

    @classmethod
    def from_settings(cls, settings: ContextSettings) -> "RedisStore":
        import redis

        if settings.redis_url:
            client = redis.Redis.from_url(settings.redis_url, socket_timeout=0.5, socket_connect_timeout=0.5)
        else:
            client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD") or None, socket_timeout=0.5, socket_connect_timeout=0.5,
            )
        return cls(client, settings.store_ttl_s, settings.store_allow_sensitive)

    def put(self, ref: str, payload: dict, sensitive: bool = False) -> bool:
        if sensitive and not self.allow_sensitive:
            return False
        try:
            value = json.dumps(payload, ensure_ascii=False)
            if self.ttl_s > 0:
                self.client.set(KEY_PREFIX + ref, value, ex=self.ttl_s)
            else:
                self.client.set(KEY_PREFIX + ref, value)
            return True
        except Exception as exc:
            self.errors += 1
            logger.warning("context store write failed: backend=redis error=%s", type(exc).__name__)
            return False

    def get(self, ref: str) -> Optional[dict]:
        try:
            value = self.client.get(KEY_PREFIX + ref)
        except Exception as exc:
            self.errors += 1
            logger.warning("context store read failed: backend=redis error=%s", type(exc).__name__)
            return None
        if value is None:
            return None
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return None


def build_store(settings: ContextSettings):
    if settings.store_backend == "none":
        return NullStore()
    if settings.store_backend == "redis":
        try:
            return RedisStore.from_settings(settings)
        except Exception as exc:
            logger.warning("context store: redis unavailable (%s), using the in-memory store", type(exc).__name__)
    return MemoryStore(settings.store_max_items, settings.store_ttl_s)
