from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from django.conf import settings

try:  # pragma: no cover - optional dependency during tests
    import redis
    from redis.exceptions import RedisError
except Exception:  # pragma: no cover
    redis = None
    RedisError = Exception


_CACHE_TTL = int(getattr(settings, "CHAT_CACHE_TTL", 24 * 60 * 60))
_NAMESPACE = f"{getattr(settings, 'TOKEN_NAMESPACE', 'authserver')}:chat"
_redis_client: Optional["redis.Redis"] = None


def _get_client() -> Optional["redis.Redis"]:
    global _redis_client
    if not redis:
        return None
    url = getattr(settings, "REDIS_URL", None)
    if not url:
        return None
    if _redis_client is None:
        try:
            _redis_client = redis.Redis.from_url(url, decode_responses=True)
        except Exception:
            _redis_client = None
    return _redis_client


def _key(*segments: str) -> str:
    return ":".join([_NAMESPACE, *segments])


def _load_json(key: str) -> Optional[Any]:
    client = _get_client()
    if not client:
        return None
    try:
        raw = client.get(key)
    except RedisError:
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            client.delete(key)
        except RedisError:
            pass
        return None


def _store_json(key: str, data: Any) -> None:
    client = _get_client()
    if not client:
        return
    try:
        client.set(key, json.dumps(data, ensure_ascii=False), ex=_CACHE_TTL)
    except RedisError:
        pass


def _touch(key: str) -> None:
    client = _get_client()
    if not client:
        return
    try:
        client.expire(key, _CACHE_TTL)
    except RedisError:
        pass


def get_cached_sessions(user_id: str) -> Optional[List[Dict[str, Any]]]:
    return _load_json(_key("sessions", user_id))


def set_cached_sessions(user_id: str, sessions: List[Dict[str, Any]]) -> None:
    _store_json(_key("sessions", user_id), sessions)


def invalidate_sessions_cache(user_id: str) -> None:
    client = _get_client()
    if not client:
        return
    try:
        client.delete(_key("sessions", user_id))
    except RedisError:
        pass


def upsert_cached_session(user_id: str, conversation: Dict[str, Any]) -> None:
    if not conversation:
        return
    conv_id = conversation.get("conversation_id")
    if not conv_id:
        return
    sessions = get_cached_sessions(user_id) or []
    sessions = [item for item in sessions if item.get("conversation_id") != conv_id]
    sessions.insert(0, conversation)
    set_cached_sessions(user_id, sessions)


def update_cached_session(
    user_id: str,
    conversation_id: str,
    *,
    title: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> None:
    sessions = get_cached_sessions(user_id)
    if not sessions:
        return
    changed = False
    for item in sessions:
        if item.get("conversation_id") == conversation_id:
            if title is not None and item.get("title") != title:
                item["title"] = title
                changed = True
            if updated_at is not None and item.get("updated_at") != updated_at:
                item["updated_at"] = updated_at
                changed = True
            break
    if not changed:
        _touch(_key("sessions", user_id))
        return
    sessions.sort(key=lambda entry: entry.get("updated_at") or "", reverse=True)
    set_cached_sessions(user_id, sessions)


def get_cached_messages(user_id: str, conversation_id: str) -> Optional[List[Dict[str, Any]]]:
    return _load_json(_key("messages", user_id, conversation_id))


def set_cached_messages(
    user_id: str, conversation_id: str, messages: List[Dict[str, Any]]
) -> None:
    _store_json(_key("messages", user_id, conversation_id), messages)


def append_cached_message(
    user_id: str,
    conversation_id: str,
    message: Dict[str, Any],
) -> None:
    if not message:
        return
    key = _key("messages", user_id, conversation_id)
    existing = _load_json(key)
    if existing is None:
        _store_json(key, [message])
        return
    existing.append(message)
    _store_json(key, existing)


def invalidate_message_cache(user_id: str, conversation_id: str) -> None:
    client = _get_client()
    if not client:
        return
    try:
        client.delete(_key("messages", user_id, conversation_id))
    except RedisError:
        pass
