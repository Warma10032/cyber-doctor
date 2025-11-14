from __future__ import annotations

from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("uid", "account", "nickname", "email", "phone_number", "created_at", "last_login")
    search_fields = ("uid", "account", "nickname", "email", "phone_number")
    readonly_fields = ("created_at", "last_login")
