from __future__ import annotations

from django.contrib import admin

from .models import Conversation, Message, ModelInfo


@admin.register(ModelInfo)
class ModelInfoAdmin(admin.ModelAdmin):
    list_display = ("model_id", "model_name", "api_key")
    search_fields = ("model_name", "api_key")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("conversation_id", "user", "created_at", "updated_at")
    search_fields = ("conversation_id", "user__account", "user__uid")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("message_id", "conversation", "sender", "created_at", "model")
    search_fields = ("message_id", "conversation__conversation_id")
    list_filter = ("sender", "created_at")
    readonly_fields = ("created_at",)
