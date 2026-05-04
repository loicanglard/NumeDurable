import os

class Config:
    # SECRET_KEY stable pour éviter de perdre les sessions au redémarrage
    SECRET_KEY = os.environ.get('SECRET_KEY', 'trail-project-v1-stable-key-2024')
    
    # Base de données (SQLite local uniquement)
    DB_TYPE = 'sqlite'
    basedir = os.path.abspath(os.path.dirname(__file__))
    DATABASE = os.path.join(basedir, 'database', 'trailmemoire.db')
    
    DEBUG = True
    WTF_CSRF_ENABLED = True
    
    # Configuration des sessions
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Important : False en local (HTTP)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_PATH = '/'
    PERMANENT_SESSION_LIFETIME = 3600 * 24 * 7
    REMEMBER_COOKIE_DURATION = 3600 * 24 * 7
