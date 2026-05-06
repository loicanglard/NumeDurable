import os
import logging
from datetime import datetime
from flask import Flask, render_template, flash, redirect, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Rate limiting extension for request throttling (optional in development)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
    LIMITER_AVAILABLE = True
except ImportError:
    # If flask_limiter is not installed, disable rate limiting (dev mode)
    limiter = None
    LIMITER_AVAILABLE = False

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

    # Fail fast if SECRET_KEY is weak or missing in production
    if not app.debug and not app.config.get('TESTING'):
        sk = app.config.get('SECRET_KEY', '')
        if not sk or sk == 'Soleil1234' or len(sk) < 32:
            raise RuntimeError(
                'SECRET_KEY must be set to a strong random value in production. '
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            )

    if not app.logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
        app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    from backend.db import init_db, get_db
    
    csrf = CSRFProtect(app)
    init_db(app)

    # Initialize rate limiter if available
    if LIMITER_AVAILABLE and limiter:
        limiter.init_app(app)

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
        from backend.constants import FLASH_ERROR
        flash(f"Session expirée ou erreur de sécurité. Veuillez réessayer.", FLASH_ERROR)
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
        except Exception as e:
            app.logger.warning(f"Failed to load user {user_id}: {e}")
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
        """Page d'accueil: liste des rapports récents et statistiques."""
        rapports = []
        stats = {'sentiers_count': 0, 'users_count': 0, 'rapports_actifs_count': 0}
        
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
        except Exception as e:
            app.logger.error(f"Error loading homepage data: {e}")
            # Return empty data but don't fail the page

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
        
    @app.route('/health')
    def health():
        try:
            db = get_db()
            db.execute('SELECT 1').fetchone()
            db_status = 'ok'
        except Exception:
            db_status = 'error'
        status = 'ok' if db_status == 'ok' else 'degraded'
        return {'status': status, 'db': db_status}, 200 if status == 'ok' else 503

    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

    return app
