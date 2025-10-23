from __future__ import annotations

import json
from typing import Any, Dict, List

from django.contrib.auth import get_user_model
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.jwt_service import decode_token, TokenError

from .models import Account, Conversation, Message, ModelInfo

User = get_user_model()


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


def _get_or_create_account(user: User) -> Account:
    account, created = Account.objects.get_or_create(
        user=user,
        defaults={
            "account": user.username[:20],
            "nickname": user.username[:20],
            "email": user.email[:30] if user.email else "",
        },
    )
    if created:
        account.last_login_at = timezone.now()
        account.save(update_fields=["last_login_at"])
    return account


def jwt_required(view_func):
    def wrapped(request: HttpRequest, *args, **kwargs):
        header = _authorization_header(request)
        if not header or not header.startswith("Bearer "):
            return _json_response({"detail": "Authorization header missing"}, status=401)
        token = header.split(" ", 1)[1]
        try:
            payload = decode_token(token, expected_type="access")
            user = User.objects.get(pk=payload["sub"])
        except (TokenError, User.DoesNotExist):
            return _json_response({"detail": "Invalid or expired token"}, status=401)

        request.user = user  # type: ignore[attr-defined]
        request.account = _get_or_create_account(user)  # type: ignore[attr-defined]
        return view_func(request, *args, **kwargs)

    return wrapped


def _conversation_to_dict(conv: Conversation) -> Dict[str, Any]:
    return {
        "id": conv.id,
        "title": conv.title,
        "user_id": conv.account.user_code,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
    }


def _message_to_dict(msg: Message) -> Dict[str, Any]:
    return {
        "id": msg.id,
        "sender": msg.sender,
        "content": msg.content,
        "created_at": msg.created_at.isoformat(),
        "model_id": msg.model_id,
    }


@csrf_exempt
@jwt_required
@require_http_methods(["GET", "POST"])
def sessions_view(request: HttpRequest) -> JsonResponse:
    account: Account = request.account  # type: ignore[attr-defined]

    if request.method == "GET":
        conversations = Conversation.objects.filter(account=account)
        return _json_response({"sessions": [_conversation_to_dict(conv) for conv in conversations]})

    try:
        payload = _parse_json(request)
    except ValueError as exc:
        return _json_response({"detail": str(exc)}, status=400)

    title = (payload.get("title") or "").strip()
    conversation = Conversation.objects.create(account=account, title=title)
    return _json_response(_conversation_to_dict(conversation), status=201)


@csrf_exempt
@jwt_required
@require_http_methods(["GET", "POST"])
def messages_view(request: HttpRequest, conversation_id: str) -> JsonResponse:
    account: Account = request.account  # type: ignore[attr-defined]

    try:
        conversation = Conversation.objects.get(id=conversation_id, account=account)
    except Conversation.DoesNotExist:
        return _json_response({"detail": "Conversation not found"}, status=404)

    if request.method == "GET":
        messages = conversation.messages.select_related("model")
        return _json_response({"messages": [_message_to_dict(msg) for msg in messages]})

    try:
        payload = _parse_json(request)
    except ValueError as exc:
        return _json_response({"detail": str(exc)}, status=400)

    sender = payload.get("sender")
    if sender not in {"user", "assistant"}:
        return _json_response({"detail": "sender must be 'user' or 'assistant'"}, status=400)

    content = (payload.get("content") or "").strip()
    if not content:
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
        content=content,
        model=model_instance,
    )

    # 更新会话更新时间
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())

    return _json_response(_message_to_dict(message), status=201)
