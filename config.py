import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'trail-project-v1-stable-key-2024')

    DATABASE_URL = os.environ.get('DATABASE_URL')
    basedir = os.path.abspath(os.path.dirname(__file__))
    DATABASE = os.path.join(basedir, 'database', 'trailmemoire.db')

    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    WTF_CSRF_ENABLED = True


    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # True en production (HTTPS sur Vercel), False en local (HTTP)
    SESSION_COOKIE_SECURE = bool(os.environ.get('DATABASE_URL'))
    SESSION_COOKIE_PATH = '/'
    PERMANENT_SESSION_LIFETIME = 3600 * 24 * 7
    REMEMBER_COOKIE_DURATION = 3600 * 24 * 7