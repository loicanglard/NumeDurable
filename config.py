import os

class Config:
    # SECRET_KEY stable pour éviter de perdre les sessions au redémarrage
    SECRET_KEY = os.environ.get('SECRET_KEY', 'trail-project-v1-stable-key-2024')
    
    # Détection environnement Vercel / Render
    IS_SERVERLESS = os.environ.get('VERCEL') or os.environ.get('RENDER')
    
    # Par défaut, on utilise SQLite pour la stabilité du MVP
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # Force SQLite en local, n'utilise Postgres que si DATABASE_URL est explicitement présent et qu'on n'est pas en local
    if DATABASE_URL and IS_SERVERLESS:
        DATABASE = DATABASE_URL
        DB_TYPE = 'postgres'
    else:
        DB_TYPE = 'sqlite'
        DATABASE = 'database/trailmemoire.db'
        
    DEBUG = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    WTF_CSRF_ENABLED = True
    
    # Configuration des sessions - Optimisée pour le local (HTTP)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # False pour autoriser les sessions en HTTP local
    SESSION_COOKIE_PATH = '/'
    PERMANENT_SESSION_LIFETIME = 3600 * 24 * 7
    REMEMBER_COOKIE_DURATION = 3600 * 24 * 7
