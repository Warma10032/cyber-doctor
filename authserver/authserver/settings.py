from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# Load environment variables from project root .env if present
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _split_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "replace-me-with-a-secure-secret")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() in {"1", "true", "yes", "on"}

ALLOWED_HOSTS = _split_csv(os.environ.get("DJANGO_ALLOWED_HOSTS")) or ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users.apps.UsersConfig",
    "chat.apps.ChatConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "authserver.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "authserver.wsgi.application"
ASGI_APPLICATION = "authserver.asgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DJANGO_DB_NAME", "cyber_doctor"),
        "USER": os.environ.get("DJANGO_DB_USER", "root"),
        "PASSWORD": os.environ.get("DJANGO_DB_PASSWORD", "123456"),
        "HOST": os.environ.get("DJANGO_DB_HOST", "114.215.183.142"),
        "PORT": os.environ.get("DJANGO_DB_PORT", "3306"),
        "OPTIONS": {
            "charset": os.environ.get("DJANGO_DB_CHARSET", "utf8mb4"),
            "init_command": os.environ.get(
                "DJANGO_DB_INIT_COMMAND", "SET sql_mode='STRICT_TRANS_TABLES'"
            ),
        },
        "CONN_MAX_AGE": int(os.environ.get("DJANGO_DB_CONN_MAX_AGE", "60")),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = os.environ.get("DJANGO_LANGUAGE_CODE", "zh-hans")
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "Asia/Shanghai")
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATIC_ROOT = os.environ.get("DJANGO_STATIC_ROOT", str(BASE_DIR / "static"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === JWT / Redis settings ===
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "replace-me-with-a-secure-jwt-secret")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_LIFETIME_MINUTES = int(os.environ.get("ACCESS_TOKEN_LIFETIME_MINUTES", "60"))
REFRESH_TOKEN_LIFETIME_DAYS = int(os.environ.get("REFRESH_TOKEN_LIFETIME_DAYS", "7"))
REDIS_URL = os.environ.get("REDIS_URL")
TOKEN_NAMESPACE = os.environ.get("AUTH_TOKEN_NAMESPACE", "authserver")
