import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')
    
    # Détection environnement Vercel / Render
    IS_SERVERLESS = os.environ.get('VERCEL') or os.environ.get('RENDER')
    
    if IS_SERVERLESS:
        DATABASE = '/tmp/trailmemoire.db'
    else:
        # En local, on assure que le dossier database existe ou on utilise un chemin relatif simple
        DATABASE = os.environ.get('DATABASE_URL', 'database/trailmemoire.db')
        
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    WTF_CSRF_ENABLED = True
