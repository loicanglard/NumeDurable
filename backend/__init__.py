import os
from datetime import datetime
from flask import Flask, render_template, render_template_string, flash, redirect, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

def create_app():
    # Détermination du projet root de manière robuste
    # Ce fichier est dans backend/, donc le root est le parent.
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    app = Flask(
        "trail_app",
        root_path=project_root,
        template_folder='frontend/templates',
        static_folder='frontend/static'
    )
    
    # Chargement de la config
    app.config.from_object('config.Config')
    
    # Sécurité supplémentaire pour la SECRET_KEY sur Vercel
    if not app.config.get('SECRET_KEY') or app.config.get('SECRET_KEY') == 'dev-secret-change-in-prod':
        if os.environ.get('VERCEL'):
            # En prod Vercel, on veut éviter de tourner avec la clé par défaut si possible
            # Mais on ne bloque pas, on utilise ce qu'on a.
            pass

    from backend.db import init_db, get_db
    
    csrf = CSRFProtect(app)
    init_db(app)

    # Flask-Login setup
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.connexion'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'info'

    from backend.models import User
    from backend.routes.auth import auth_bp
    from backend.routes.users import users_bp
    from backend.routes.sentiers import sentiers_bp
    from backend.routes.rapports import rapports_bp
    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        import sys
        flash(f"Session expirée ou erreur de sécurité. Veuillez réessayer. ({e.description})", 'erreur')
        return redirect(request.url)

    @login_manager.user_loader
    def load_user(user_id):
        if not user_id:
            return None
        try:
            db = get_db()
            # On utilise 'users' car c'est le nouveau standard du projet compatible Postgres/SQLite
            row = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
            if row:
                return User(row)
        except Exception:
            # Fallback vers 'user' si 'users' n'existe pas encore dans la BDD locale
            try:
                row = db.execute('SELECT * FROM "user" WHERE id = ?', (user_id,)).fetchone()
                if row:
                    return User(row)
            except Exception:
                pass
        return None

    # Error logging global pour debugger les 500 sur Vercel
    @app.errorhandler(500)
    def internal_error(error):
        import traceback
        import sys
        tb = traceback.format_exc()
        print("--- TRACEBACK 500 ---", file=sys.stderr)
        print(tb, file=sys.stderr)
        
        template = """
        {% extends "base.html" %}
        {% block contenu %}
        <div class="card mt-4">
            <h1 style="color: var(--status-red);">Oups ! Une erreur interne est survenue.</h1>
            <p class="text-soft mt-1">Détails de l'erreur pour le debug :</p>
            <pre style="background: #111; color: #ff5555; padding: 1rem; border-radius: 5px; overflow-x: auto; font-family: monospace; font-size: 0.85rem; margin-top: 1rem;">
{{ traceback }}
            </pre>
            <div class="mt-2">
                <a href="/" class="btn btn-primary">Retour à l'accueil</a>
            </div>
        </div>
        {% endblock %}
        """
        return render_template_string(template, traceback=tb), 500

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(sentiers_bp)
    app.register_blueprint(rapports_bp)

    @app.route('/')
    def index():
        try:
            db = get_db()
            rapports = db.execute('''
                SELECT r.*, s.nom as sentier_nom, s.region, u.nom as user_nom,
                       ROUND((julianday('now') - julianday(r.date_rapport)) * 24) as heures
                FROM rapport r
                JOIN sentier s ON r.sentier_id = s.id
                JOIN users u ON r.user_id = u.id
                WHERE r.date_expiration > datetime('now')
                ORDER BY r.date_rapport DESC
                LIMIT 5
            ''').fetchall()
        except Exception:
            # Si la base n'est pas encore prête ou vide
            rapports = []

        rapports_recents = []
        for r in rapports:
            h = r['heures'] or 0
            if h < 1:
                anciennete = "moins d'1h"
            elif h < 24:
                anciennete = f"{int(h)}h"
            else:
                jours = int(h // 24)
                anciennete = f"{jours}j"
            rapports_recents.append({**dict(r), 'anciennete': anciennete})

        return render_template('index.html', rapports_recents=rapports_recents)

    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

    return app
