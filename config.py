import os
import secrets
from datetime import timedelta



class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    # Prefer SUPABASE settings (URL + KEY). If not present, fall back to DATABASE_URL.
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

    DATABASE = os.environ.get('DATABASE_URL')
    if not (DATABASE or (SUPABASE_URL and SUPABASE_KEY)):
        raise ValueError("Either DATABASE_URL or SUPABASE_URL + SUPABASE_KEY must be set in your environment.")

    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    WTF_CSRF_ENABLED = True

    # Configuration des sessions - secure defaults for production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in ('1', 'true', 'yes')
    SESSION_COOKIE_PATH = '/'
    PERMANENT_SESSION_LIFETIME = int(os.environ.get('PERMANENT_SESSION_LIFETIME', 3600))  # seconds, default 1h
    REMEMBER_COOKIE_DURATION = int(os.environ.get('REMEMBER_COOKIE_DURATION', 3600 * 24 * 7))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    # Ensure secure cookie in production
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True