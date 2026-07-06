"""
Django settings for the Heat Stress / Climate Monitor project.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Φορτώνει αυτόματα το αρχείο .env (αν υπάρχει) σε environment variables, ώστε
# να ΜΗΝ χρειάζεται κανένα χειροκίνητο "export" (που ούτως ή άλλως δεν δουλεύει
# στα Windows) - λειτουργεί ίδια σε Windows/Mac/Linux.
load_dotenv(BASE_DIR / ".env")

# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "monitor",
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

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "monitor" / "templates"],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --------------------------------------------------------------------------
# Database (SQLite by default; point DATABASE_URL-style env vars to switch)
# --------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "monitor" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------
# REST framework
# --------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# --------------------------------------------------------------------------
# Notifications (SMS μέσω InfiniReach - infinireach.io, χρησιμοποιεί το δικό
# σου Android κινητό/SIM ως πύλη SMS, δωρεάν πλάνο διαθέσιμο)
# --------------------------------------------------------------------------
INFINIREACH_API_KEY = os.environ.get("INFINIREACH_API_KEY", "")
INFINIREACH_FROM_NUMBER = os.environ.get("INFINIREACH_FROM_NUMBER", "")  # ο αριθμός SIM του κινητού σου, π.χ. +35799xxxxxx

# Minimum minutes between two notifications of the SAME signal level for the
# SAME device, so you don't get spammed every time a reading comes in.
NOTIFICATION_COOLDOWN_MINUTES = int(os.environ.get("NOTIFICATION_COOLDOWN_MINUTES", "15"))

# If a device sends nothing for this many minutes, the dashboard marks it offline.
DEVICE_OFFLINE_AFTER_MINUTES = int(os.environ.get("DEVICE_OFFLINE_AFTER_MINUTES", "10"))

# --------------------------------------------------------------------------
# Logging - χωρίς αυτό, τα logger.info(...) μέσα στο monitor/views.py και
# monitor/services.py (π.χ. "Ecowitt: άγνωστο PASSKEY...") ΔΕΝ εμφανίζονται
# πουθενά. Με αυτό, θα τα βλέπεις ζωντανά στην ίδια κονσόλα που τρέχει
# το `python manage.py runserver`.
# --------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}