from __future__ import annotations

import uuid

from django.db import models

from users.models import User


def _short_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def generate_conversation_id() -> str:
    return _short_id("conv")


def generate_message_id() -> str:
    return _short_id("msg")


class ModelInfo(models.Model):
    model_id = models.AutoField(primary_key=True)
    model_name = models.CharField(max_length=25)
    description = models.TextField(blank=True)
    api_key = models.CharField(max_length=50)

    class Meta:
        db_table = "model"

    def __str__(self) -> str:  # pragma: no cover
        return self.model_name


class Conversation(models.Model):
    conversation_id = models.CharField(
        primary_key=True,
        max_length=50,
        default=generate_conversation_id,
        editable=False,
    )
    user = models.ForeignKey(
        User,
        db_column="uid",
        to_field="uid",
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversation"
        ordering = ["-updated_at"]

    def __str__(self) -> str:  # pragma: no cover
        return self.conversation_id


class Message(models.Model):
    message_id = models.CharField(
        primary_key=True,
        max_length=50,
        default=generate_message_id,
        editable=False,
    )
    conversation = models.ForeignKey(
        Conversation,
        db_column="conversation_id",
        to_field="conversation_id",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.BooleanField()
    message_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    model = models.ForeignKey(
        ModelInfo,
        db_column="model_id",
        to_field="model_id",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="messages",
    )

    class Meta:
        db_table = "message"
        ordering = ["created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return self.message_id
