from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any, Dict, Optional, Tuple

from django.contrib.auth import authenticate, get_user_model
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from chat.models import Account
from core.jwt_service import (
    TokenError,
    decode_token,
    generate_token_pair,
    refresh_from_token,
    revoke_tokens,
)

User = get_user_model()


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
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON body")


def _extract_credentials(data: Dict[str, Any]) -> Tuple[str, str]:
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        raise ValueError("Username and password are required")
    return username, password


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
        username, password = _extract_credentials(payload)
    except ValueError as exc:
        return _error(str(exc), HTTPStatus.BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return _error("Username already exists", HTTPStatus.CONFLICT)

    user = User.objects.create_user(username=username, password=password)
    Account.objects.create(
        user=user,
        account=username[:20],
        nickname=username[:20],
        email=user.email[:30] if user.email else "",
    )

    return _json_response(
        {
            "id": user.pk,
            "username": user.get_username(),
            "detail": "User registered successfully",
        },
        status=HTTPStatus.CREATED,
    )


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = _parse_json(request)
        username, password = _extract_credentials(payload)
    except ValueError as exc:
        return _error(str(exc), HTTPStatus.BAD_REQUEST)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return _error("Invalid credentials", HTTPStatus.UNAUTHORIZED)

    Account.objects.get_or_create(
        user=user,
        defaults={
            "account": username[:20],
            "nickname": username[:20],
            "email": user.email[:30] if user.email else "",
        },
    )

    pair = generate_token_pair(user)
    return _json_response(
        {
            "user": {"id": user.pk, "username": user.get_username()},
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
            "user": {"id": user.pk, "username": user.get_username()},
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
        user = User.objects.get(pk=payload["sub"])
    except (TokenError, User.DoesNotExist):
        return _error("Invalid or expired token", HTTPStatus.UNAUTHORIZED)

    return _json_response(
        {
            "id": user.pk,
            "username": user.get_username(),
        }
    )
