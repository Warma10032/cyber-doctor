from __future__ import annotations

import json
from typing import Any, Dict

from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.jwt_service import decode_token, TokenError

from users.models import User

from .models import Conversation, Message, ModelInfo
from .cache import (
    append_cached_message,
    get_cached_messages,
    get_cached_sessions,
    set_cached_messages,
    set_cached_sessions,
    update_cached_session,
    upsert_cached_session,
)


def _json_response(data: Any, *, status: int = 200) -> JsonResponse:
    return JsonResponse(data, status=status, safe=isinstance(data, dict))


def _parse_json(request: HttpRequest) -> Dict[str, Any]:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON body") from exc


def _authorization_header(request: HttpRequest) -> str | None:
    return request.headers.get("Authorization") or request.META.get("HTTP_AUTHORIZATION")


def jwt_required(view_func):
    def wrapped(request: HttpRequest, *args, **kwargs):
        header = _authorization_header(request)
        if not header or not header.startswith("Bearer "):
            return _json_response({"detail": "Authorization header missing"}, status=401)
        token = header.split(" ", 1)[1]
        try:
            payload = decode_token(token, expected_type="access")
            user = User.objects.get(uid=payload["sub"])
        except (TokenError, User.DoesNotExist):
            return _json_response({"detail": "Invalid or expired token"}, status=401)

        request.user = user  # type: ignore[attr-defined]
        return view_func(request, *args, **kwargs)

    return wrapped


def _conversation_to_dict(conv: Conversation) -> Dict[str, Any]:
    return {
        "conversation_id": conv.conversation_id,
        "uid": conv.user_id,
        "title": conv.title or "",
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
    }


def _message_to_dict(msg: Message) -> Dict[str, Any]:
    return {
        "message_id": msg.message_id,
        "sender": "user" if msg.sender else "assistant",
        "message_text": msg.message_text,
        "created_at": msg.created_at.isoformat(),
        "model_id": msg.model_id,
    }


@csrf_exempt
@jwt_required
@require_http_methods(["GET", "POST"])
def sessions_view(request: HttpRequest) -> JsonResponse:
    user: User = request.user  # type: ignore[attr-defined]
    user_id = str(user.uid)

    if request.method == "GET":
        cached = get_cached_sessions(user_id)
        if cached is not None:
            return _json_response({"sessions": cached})
        conversations = Conversation.objects.filter(user=user)
        serialized = [_conversation_to_dict(conv) for conv in conversations]
        set_cached_sessions(user_id, serialized)
        return _json_response({"sessions": serialized})

    try:
        payload = _parse_json(request)
    except ValueError as exc:
        return _json_response({"detail": str(exc)}, status=400)

    conversation_id = payload.get("conversation_id")
    raw_title = (payload.get("title") or "").strip()
    if len(raw_title) > 100:
        return _json_response({"detail": "title 最长 100 个字符"}, status=400)

    create_kwargs = {"user": user, "title": raw_title}
    if conversation_id:
        create_kwargs["conversation_id"] = conversation_id
    conversation = Conversation.objects.create(**create_kwargs)
    serialized = _conversation_to_dict(conversation)
    upsert_cached_session(user_id, serialized)
    return _json_response(serialized, status=201)


@csrf_exempt
@jwt_required
@require_http_methods(["GET", "PATCH"])
def session_detail_view(request: HttpRequest, conversation_id: str) -> JsonResponse:
    user: User = request.user  # type: ignore[attr-defined]
    user_id = str(user.uid)

    try:
        conversation = Conversation.objects.get(conversation_id=conversation_id, user=user)
    except Conversation.DoesNotExist:
        return _json_response({"detail": "Conversation not found"}, status=404)

    if request.method == "GET":
        return _json_response(_conversation_to_dict(conversation))

    try:
        payload = _parse_json(request)
    except ValueError as exc:
        return _json_response({"detail": str(exc)}, status=400)

    new_title = (payload.get("title") or "").strip()
    if len(new_title) > 100:
        return _json_response({"detail": "title 最长 100 个字符"}, status=400)

    Conversation.objects.filter(pk=conversation.pk).update(title=new_title)
    conversation.title = new_title
    update_cached_session(user_id, conversation.conversation_id, title=new_title)
    return _json_response(_conversation_to_dict(conversation))


@csrf_exempt
@jwt_required
@require_http_methods(["GET", "POST"])
def messages_view(request: HttpRequest, conversation_id: str) -> JsonResponse:
    user: User = request.user  # type: ignore[attr-defined]
    user_id = str(user.uid)

    try:
        conversation = Conversation.objects.get(conversation_id=conversation_id, user=user)
    except Conversation.DoesNotExist:
        return _json_response({"detail": "Conversation not found"}, status=404)

    if request.method == "GET":
        cached = get_cached_messages(user_id, conversation_id)
        if cached is not None:
            return _json_response({"messages": cached})
        messages = conversation.messages.select_related("model")
        serialized = [_message_to_dict(msg) for msg in messages]
        set_cached_messages(user_id, conversation_id, serialized)
        return _json_response({"messages": serialized})

    try:
        payload = _parse_json(request)
    except ValueError as exc:
        return _json_response({"detail": str(exc)}, status=400)

    sender_value = payload.get("sender")
    if sender_value not in {"user", "assistant", True, False}:
        return _json_response({"detail": "sender must be 'user' or 'assistant'"}, status=400)

    sender = True if sender_value in {"user", True} else False

    message_text = (payload.get("message_text") or payload.get("content") or "").strip()
    if not message_text:
        return _json_response({"detail": "content is required"}, status=400)

    model_id = payload.get("model_id")
    model_instance = None
    if model_id is not None:
        try:
            model_instance = ModelInfo.objects.get(pk=model_id)
        except ModelInfo.DoesNotExist:
            return _json_response({"detail": "model not found"}, status=400)

    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        message_text=message_text,
        model=model_instance,
    )

    # 更新会话更新时间
    now = timezone.now()
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=now)
    conversation.updated_at = now

    serialized_message = _message_to_dict(message)
    append_cached_message(user_id, conversation.conversation_id, serialized_message)
    update_cached_session(
        user_id,
        conversation.conversation_id,
        updated_at=conversation.updated_at.isoformat(),
    )

    return _json_response(serialized_message, status=201)
