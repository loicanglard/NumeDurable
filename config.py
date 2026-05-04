import os

class Config:
    # SECRET_KEY stable pour éviter de perdre les sessions au redémarrage
    SECRET_KEY = os.environ.get('SECRET_KEY', 'trail-project-v1-stable-key-2024')
    
    # Détection environnement Vercel / Render
    IS_SERVERLESS = os.environ.get('VERCEL') or os.environ.get('RENDER')
    
    # Choix de la base de données
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        # Si une URL est fournie, on l'utilise (Postgres sur Vercel/Supabase)
        DATABASE = DATABASE_URL
        DB_TYPE = 'postgres'
    else:
        # Sinon SQLite par défaut
        DB_TYPE = 'sqlite'
        if IS_SERVERLESS:
            # Sur Vercel, SQLite ne peut écrire que dans /tmp
            DATABASE = '/tmp/trailmemoire.db'
        else:
            # En local, on utilise le dossier database/ de manière robuste (chemin absolu)
            basedir = os.path.abspath(os.path.dirname(__file__))
            DATABASE = os.path.join(basedir, 'database', 'trailmemoire.db')
        
    DEBUG = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    WTF_CSRF_ENABLED = True
    
    # Configuration des sessions
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Important : True sur Vercel (HTTPS), False en local (HTTP)
    SESSION_COOKIE_SECURE = True if IS_SERVERLESS else False
    SESSION_COOKIE_PATH = '/'
    PERMANENT_SESSION_LIFETIME = 3600 * 24 * 7
    REMEMBER_COOKIE_DURATION = 3600 * 24 * 7
