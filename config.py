import os

class Config:
    # SECRET_KEY stable pour éviter de perdre les sessions au redémarrage
    SECRET_KEY = os.environ.get('SECRET_KEY', 'trail-project-v1-stable-key-2024')
    
    # Détection environnement Vercel / Render
    IS_SERVERLESS = os.environ.get('VERCEL') or os.environ.get('RENDER')
    
    if IS_SERVERLESS:
        DATABASE = '/tmp/trailmemoire.db'
    else:
        # En local, on assure que le dossier database existe ou on utilise un chemin relatif simple
        DATABASE = os.environ.get('DATABASE_URL', 'database/trailmemoire.db')
        
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    WTF_CSRF_ENABLED = True
    
    # Configuration des sessions pour plus de stabilité
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600 * 24 * 7 # 7 jours
