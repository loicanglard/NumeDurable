import os

class Config:
    # SECRET_KEY stable pour éviter de perdre les sessions au redémarrage
    SECRET_KEY = os.environ.get('SECRET_KEY', 'trail-project-v1-stable-key-2024')
    
    # Détection environnement Vercel / Render
    IS_SERVERLESS = os.environ.get('VERCEL') or os.environ.get('RENDER')
    
    # URL de base de données (PostgreSQL en prod, SQLite en local)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        DATABASE = DATABASE_URL
        DB_TYPE = 'postgres'
    elif IS_SERVERLESS:
        DATABASE = '/tmp/trailmemoire.db'
        DB_TYPE = 'sqlite'
    else:
        DATABASE = os.environ.get('DATABASE_URL', 'database/trailmemoire.db')
        DB_TYPE = 'sqlite'
        
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    WTF_CSRF_ENABLED = True
    
    # Configuration des sessions
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600 * 24 * 7
