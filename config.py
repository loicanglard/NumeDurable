import os
from datetime import timedelta


class Config:
    # SECRET_KEY must come from environment in production; fallback to a
    # generated key for development only (not committed).
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24).hex()

    # Base de données (SQLite local par défaut)
    DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')
    basedir = os.path.abspath(os.path.dirname(__file__))
    DATABASE = os.environ.get('DATABASE') or os.path.join(basedir, 'database', 'trailmemoire.db')

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