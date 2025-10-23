from __future__ import annotations

import uuid
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


def _short_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def generate_user_id() -> str:
    return uuid.uuid4().hex[:10]


def generate_conversation_id() -> str:
    return _short_id("conv")


def generate_message_id() -> str:
    return _short_id("msg")


class Account(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="account",
        db_column="auth_user_id",
    )
    user_code = models.CharField(
        max_length=10,
        primary_key=True,
        default=generate_user_id,
        editable=False,
        db_column="user_id",
    )
    account = models.CharField(max_length=20, unique=True)
    nickname = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=30, blank=True)
    wechat = models.CharField(max_length=30, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "account"

    def __str__(self) -> str:  # pragma: no cover - human readable
        return self.account


class ModelInfo(models.Model):
    name = models.CharField(max_length=25)
    description = models.TextField(blank=True)
    api = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "model_info"

    def __str__(self) -> str:  # pragma: no cover - human readable
        return self.name


class Conversation(models.Model):
    id = models.CharField(primary_key=True, max_length=50, default=generate_conversation_id, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="conversations")
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversation"
        ordering = ["-updated_at"]

    def __str__(self) -> str:  # pragma: no cover - human readable
        return self.title or self.id


class Message(models.Model):
    SENDER_CHOICES = (
        ("user", "User"),
        ("assistant", "Assistant"),
    )

    id = models.CharField(primary_key=True, max_length=50, default=generate_message_id, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    model = models.ForeignKey(ModelInfo, null=True, blank=True, on_delete=models.SET_NULL, related_name="messages")

    class Meta:
        db_table = "message"
        ordering = ["created_at"]

    def __str__(self) -> str:  # pragma: no cover - human readable
        return f"{self.sender}: {self.content[:20]}"
