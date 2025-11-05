from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any, Dict, Optional, Tuple

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.jwt_service import (
    TokenError,
    decode_token,
    generate_token_pair,
    refresh_from_token,
    revoke_tokens,
)
from users.models import User


def _json_response(
    data: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK
) -> JsonResponse:
    return JsonResponse(data, status=status.value)


def _error(message: str, status: HTTPStatus) -> JsonResponse:
    return _json_response({"detail": message}, status)


def _parse_json(request: HttpRequest) -> Dict[str, Any]:
    try:
        if not request.body:
            return {}
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON body") from exc


def _extract_credentials(data: Dict[str, Any]) -> Tuple[str, str]:
    account = data.get("username") or data.get("account") or ""
    account = account.strip()
    password = data.get("password", "")
    if not account or not password:
        raise ValueError("Username/account and password are required")
    return account, password


def _get_bearer_token(request: HttpRequest) -> Optional[str]:
    auth_header = request.headers.get("Authorization") or request.META.get(
        "HTTP_AUTHORIZATION"
    )
    if not auth_header:
        return None
    prefix = "Bearer "
    if auth_header.startswith(prefix):
        return auth_header[len(prefix) :].strip()
    return None


@csrf_exempt
@require_http_methods(["POST"])
def register_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = _parse_json(request)
        account, password = _extract_credentials(payload)
    except ValueError as exc:
        return _error(str(exc), HTTPStatus.BAD_REQUEST)

    if User.objects.filter(account=account).exists():
        return _error("Account already exists", HTTPStatus.CONFLICT)

    user = User(
        account=account[:20],
        nickname=(payload.get("nickname") or account)[:20],
        email=(payload.get("email") or "")[:30],
        wx_id=(payload.get("wx_id") or "")[:30],
        phone_number=(payload.get("phone_number") or "")[:20],
    )
    user.set_password(password)
    user.save()

    return _json_response(
        {
            "uid": user.uid,
            "account": user.account,
            "detail": "User registered successfully",
        },
        status=HTTPStatus.CREATED,
    )


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = _parse_json(request)
        account, password = _extract_credentials(payload)
    except ValueError as exc:
        return _error(str(exc), HTTPStatus.BAD_REQUEST)

    try:
        user = User.objects.get(account=account)
    except User.DoesNotExist:
        return _error("Invalid credentials", HTTPStatus.UNAUTHORIZED)

    if not user.check_password(password):
        return _error("Invalid credentials", HTTPStatus.UNAUTHORIZED)

    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])

    pair = generate_token_pair(user)
    return _json_response(
        {
            "user": {"uid": user.uid, "account": user.account},
            "access_token": pair.access_token,
            "refresh_token": pair.refresh_token,
            "access_expires_in": pair.access_expires_in,
            "refresh_expires_in": pair.refresh_expires_in,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def refresh_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = _parse_json(request)
    except ValueError as exc:
        return _error(str(exc), HTTPStatus.BAD_REQUEST)

    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        return _error("refresh_token is required", HTTPStatus.BAD_REQUEST)

    try:
        user, pair = refresh_from_token(refresh_token)
    except TokenError as exc:
        return _error(str(exc), HTTPStatus.UNAUTHORIZED)

    return _json_response(
        {
            "user": {"uid": user.uid, "account": user.account},
            "access_token": pair.access_token,
            "refresh_token": pair.refresh_token,
            "access_expires_in": pair.access_expires_in,
            "refresh_expires_in": pair.refresh_expires_in,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> JsonResponse:
    access_token = _get_bearer_token(request)
    try:
        payload = _parse_json(request)
    except ValueError:
        payload = {}
    refresh_token = payload.get("refresh_token")

    revoke_tokens(access_token, refresh_token)
    return HttpResponse(status=HTTPStatus.NO_CONTENT.value)


@require_http_methods(["GET"])
def me_view(request: HttpRequest) -> JsonResponse:
    token = _get_bearer_token(request)
    if not token:
        return _error("Authorization header missing", HTTPStatus.UNAUTHORIZED)

    try:
        payload = decode_token(token, expected_type="access")
        user = User.objects.get(uid=payload["sub"])
    except (TokenError, User.DoesNotExist):
        return _error("Invalid or expired token", HTTPStatus.UNAUTHORIZED)

    return _json_response({"uid": user.uid, "account": user.account})
