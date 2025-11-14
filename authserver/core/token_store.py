from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Optional

from django.conf import settings

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover - redis is optional at runtime
    redis = None


class TokenStore:
    """
    Persistence layer for refresh tokens and access token blacklist.

    Redis is preferred when available. When REDIS_URL is not configured or the
    redis library is absent, a thread-safe JSON file fallback is used so the
    service stays functional in development environments.
    """

    def __init__(self) -> None:
        self._namespace = settings.TOKEN_NAMESPACE
        self._redis = self._init_redis()
        self._lock = threading.Lock()
        self._memory_path = Path(settings.BASE_DIR) / "token_store.json"
        if not self._memory_path.exists():
            self._memory_path.write_text(json.dumps({"refresh": {}, "blacklist": {}}))

    def _init_redis(self) -> Optional["redis.Redis"]:
        if not settings.REDIS_URL or redis is None:
            return None
        return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    # -- public API -----------------------------------------------------

    def store_refresh(self, jti: str, user_id: str, expires_in: int) -> None:
        payload = json.dumps({"user_id": user_id})
        key = self._refresh_key(jti)
        self._set_with_ttl(key, payload, expires_in)

    def revoke_refresh(self, jti: str) -> None:
        key = self._refresh_key(jti)
        self._delete(key)

    def get_refresh_owner(self, jti: str) -> Optional[str]:
        raw = self._get(self._refresh_key(jti))
        if raw is None:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data.get("user_id")

    def blacklist_access(self, jti: str, expires_in: int) -> None:
        key = self._blacklist_key(jti)
        self._set_with_ttl(key, "revoked", expires_in)

    def is_access_blacklisted(self, jti: str) -> bool:
        return self._get(self._blacklist_key(jti)) is not None

    # -- redis/file operations -----------------------------------------

    def _set_with_ttl(self, key: str, value: str, ttl: int) -> None:
        if self._redis:
            self._redis.setex(key, ttl, value)
        else:
            with self._lock:
                data = self._load_memory()
                expire_at = time.time() + ttl
                data_section, item_key = self._split_key(key)
                if data_section not in data:
                    data[data_section] = {}
                data[data_section][item_key] = {"value": value, "expire_at": expire_at}
                self._dump_memory(data)

    def _get(self, key: str) -> Optional[str]:
        if self._redis:
            return self._redis.get(key)
        with self._lock:
            data = self._load_memory()
            data_section, item_key = self._split_key(key)
            section = data.get(data_section, {})
            item = section.get(item_key)
            if not item:
                return None
            if item["expire_at"] < time.time():
                # expired -> cleanup
                del section[item_key]
                self._dump_memory(data)
                return None
            return item["value"]

    def _delete(self, key: str) -> None:
        if self._redis:
            self._redis.delete(key)
        else:
            with self._lock:

                data = self._load_memory()
                data_section, item_key = self._split_key(key)
                section = data.get(data_section, {})
                if item_key in section:
                    del section[item_key]
                    self._dump_memory(data)

    # -- helpers --------------------------------------------------------

    def _refresh_key(self, jti: str) -> str:
        return f"{self._namespace}:refresh:{jti}"

    def _blacklist_key(self, jti: str) -> str:
        return f"{self._namespace}:blacklist:{jti}"

    @staticmethod
    def _split_key(key: str) -> tuple[str, str]:
        parts = key.split(":")
        if len(parts) == 1:
            return parts[0], ""
        if len(parts) == 2:
            return parts[0], parts[1]
        # expected format: namespace:section:item
        section = parts[-2]
        item = parts[-1]
        return section, item

    def _load_memory(self) -> dict[str, Any]:
        try:
            return json.loads(self._memory_path.read_text())
        except json.JSONDecodeError:
            return {"refresh": {}, "blacklist": {}}

    def _dump_memory(self, data: dict[str, Any]) -> None:
        self._memory_path.write_text(json.dumps(data))


token_store = TokenStore()
