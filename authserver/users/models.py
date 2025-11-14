from __future__ import annotations

import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.db import models


def generate_uid() -> str:
    """Generate a 10-character user identifier."""

    return uuid.uuid4().hex[:10]


class User(models.Model):
    uid = models.CharField(
        max_length=10,
        primary_key=True,
        editable=False,
        default=generate_uid,
    )
    account = models.CharField(max_length=20, unique=True)
    nickname = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=30, blank=True)
    password = models.CharField(max_length=128)
    wx_id = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user"

    def set_password(self, raw_password: str) -> None:
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password)

    def __str__(self) -> str:  # pragma: no cover - human readable
        return self.account
