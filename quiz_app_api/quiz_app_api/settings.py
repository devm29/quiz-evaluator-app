"""Django settings for the quiz_app_api project.

Every value that differs between a laptop and a deployed environment is read
from the process environment with a safe default, so the same image can run in
both places without editing code. See the configuration table in the top-level
README for the full list.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

from django.core.management.utils import get_random_secret_key

from quiz_app_api.env import env_bool, env_int, env_list, env_str

BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
DEBUG = env_bool("DJANGO_DEBUG", default=False)

SECRET_KEY = env_str("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    # Never ship a key in source control. When one is not supplied we generate
    # an ephemeral key so a fresh clone still boots and the test suite still
    # runs; outside DEBUG that is a deployment mistake, so say so loudly.
    SECRET_KEY = get_random_secret_key()
    if not DEBUG and "test" not in sys.argv:
        # The test runner generates its own throwaway state; warning there is
        # noise, not a signal.
        warnings.warn(
            "DJANGO_SECRET_KEY is not set. A random key was generated for this "
            "process: sessions and signed values will not survive a restart. "
            "Set DJANGO_SECRET_KEY before deploying.",
            RuntimeWarning,
            stacklevel=2,
        )

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "[::1]"]
)

ROOT_URLCONF = "quiz_app_api.urls"
WSGI_APPLICATION = "quiz_app_api.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "quiz",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Serves everything under STATIC_ROOT straight from gunicorn. Django's
    # staticfiles app only serves files under runserver with DEBUG on, so
    # without this the admin loads unstyled in any container deployment.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

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

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
# SQLite is a deliberate choice for this project: a single append-mostly table
# with no concurrent writers. The path is configurable so a container can point
# it at a mounted volume instead of the (ephemeral) image filesystem.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": env_str("DJANGO_SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
        "OPTIONS": {"timeout": 20},
    }
}

# --------------------------------------------------------------------------
# CORS
# --------------------------------------------------------------------------
# The browser app is served from a different origin to the API, so CORS is
# required. Default to an explicit allow-list; blanket allow-all is opt-in.
CORS_ALLOW_ALL_ORIGINS = env_bool("DJANGO_CORS_ALLOW_ALL", default=False)
CORS_ALLOWED_ORIGINS = env_list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    default=["http://localhost:8220", "http://127.0.0.1:8220"],
)

# --------------------------------------------------------------------------
# Django REST Framework
# --------------------------------------------------------------------------
# No pagination class: the only list endpoint serves the quiz itself, capped
# at QUIZ_MAX_QUESTIONS_PER_SUBMISSION. Submissions are read in the admin.
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": env_str("QUIZ_ANON_THROTTLE_RATE", "60/min")},
}

# --------------------------------------------------------------------------
# Quiz domain settings
# --------------------------------------------------------------------------
# Hard cap on a single submission so an oversized body cannot turn into an
# unbounded write loop. Five questions is the shipped quiz; 100 is head-room.
QUIZ_MAX_QUESTIONS_PER_SUBMISSION = env_int("QUIZ_MAX_QUESTIONS_PER_SUBMISSION", 100)

# Which scoring strategy grades a submission. See quiz/scoring.py. The browser
# client never computes a score, so the server marks against the catalogue.
QUIZ_SCORING_STRATEGY = env_str("QUIZ_SCORING_STRATEGY", "exact-match")

# --------------------------------------------------------------------------
# Auth / i18n / static
# --------------------------------------------------------------------------
_PASSWORD_VALIDATION = "django.contrib.auth.password_validation"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"{_PASSWORD_VALIDATION}.UserAttributeSimilarityValidator"},
    {"NAME": f"{_PASSWORD_VALIDATION}.MinimumLengthValidator"},
    {"NAME": f"{_PASSWORD_VALIDATION}.CommonPasswordValidator"},
    {"NAME": f"{_PASSWORD_VALIDATION}.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = env_str("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles"))

# Compress on collectstatic; no manifest, so a missing collectstatic degrades
# to "unhashed filenames" rather than to a 500 on every admin page.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
WHITENOISE_MAX_AGE = 0 if DEBUG else 31536000

# --------------------------------------------------------------------------
# Transport security (no-ops behind a plain HTTP dev server)
# --------------------------------------------------------------------------
# Only trust X-Forwarded-Proto when something in front is known to set it.
# Left on unconditionally, any client could claim its plain-HTTP request
# arrived over TLS.
if env_bool("DJANGO_TRUST_PROXY_SSL_HEADER", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG and env_bool("DJANGO_SECURE_COOKIES", default=False)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": env_str("DJANGO_LOG_LEVEL", "INFO")},
}
