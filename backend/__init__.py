import os
import logging
from datetime import datetime
from flask import Flask, render_template, flash, redirect, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Rate limiting extension (initialized into app in create_app)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    # Create a Limiter instance for import by routes; will be init_app(app) below
    limiter = Limiter(key_func=get_remote_address)
except Exception:
    # Fallback dummy limiter when package is not installed (development)
    class _DummyLimiter:
        def init_app(self, app):
            return None

        def limit(self, *a, **k):
            def _decorator(f):
                return f
            return _decorator

    limiter = _DummyLimiter()

def create_app():
    # Détermination du projet root de manière robuste
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    app = Flask(
        "trail_app",
        root_path=project_root,
        template_folder='frontend/templates',
        static_folder='frontend/static'
    )
    
    # Chargement de la config
    app.config.from_object('config.Config')

    if not app.logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
        app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    from backend.db import init_db, get_db
    
    csrf = CSRFProtect(app)
    init_db(app)

    # Initialize rate limiter
    try:
        limiter.init_app(app)
    except Exception:
        # If limiter cannot initialize (dev without dependency), continue silently
        pass

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
        flash(f"Session expirée ou erreur de sécurité. Veuillez réessayer.", 'erreur')
        return redirect(request.url)

    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('403.html'), 403

    @login_manager.user_loader
    def load_user(user_id):
        if not user_id:
            return None
        try:
            db = get_db()
            row = db.execute('SELECT * FROM "user" WHERE id = ?', (user_id,)).fetchone()
            if row:
                return User(row)
        except Exception:
            pass
        return None

    @app.errorhandler(500)
    def internal_error(error):
        import traceback
        # Log the exception stacktrace to the application logger
        app.logger.exception('Unhandled exception')
        # In debug mode, show the traceback in the 500 page for developers
        if app.config.get('DEBUG'):
            tb = traceback.format_exc()
            return render_template('500.html', traceback=tb), 500
        # In production, do not expose internals
        return render_template('500.html'), 500

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
                JOIN "user" u ON r.user_id = u.id
                WHERE r.date_expiration > datetime('now')
                ORDER BY r.date_rapport DESC
                LIMIT 5
            ''').fetchall()
            stats = db.execute('''
                SELECT
                    (SELECT COUNT(*) FROM sentier) AS sentiers_count,
                    (SELECT COUNT(*) FROM "user") AS users_count,
                    (SELECT COUNT(*) FROM rapport WHERE date_expiration > datetime('now')) AS rapports_actifs_count
            ''').fetchone()
        except Exception:
            rapports = []
            stats = {'sentiers_count': 0, 'users_count': 0, 'rapports_actifs_count': 0}

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

        return render_template(
            'index.html',
            rapports_recents=rapports_recents,
            stats=stats,
        )

    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

    return app
