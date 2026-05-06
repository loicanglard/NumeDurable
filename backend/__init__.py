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
    # Initialize Supabase client if credentials present
    try:
        from supabase import create_client
        supabase_url = app.config.get('SUPABASE_URL')
        supabase_key = app.config.get('SUPABASE_KEY')
        if supabase_url and supabase_key:
            app.supabase = create_client(supabase_url, supabase_key)
        else:
            app.supabase = None
    except Exception:
        app.supabase = None
    
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
            supabase = app.supabase
            if supabase:
                resp = supabase.table('user').select('*').eq('id', int(user_id)).execute()
                rows = resp.data or []
                if rows:
                    return User(rows[0])
            else:
                db = get_db()
                row = db.execute('SELECT * FROM "user" WHERE id = %s', (user_id,)).fetchone()
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
            supabase = app.supabase
            if supabase:
                now = datetime.utcnow().isoformat()
                rapports_resp = supabase.table('rapport').select('*').gt('date_expiration', now).order('date_rapport', desc=True).limit(5).execute()
                rapports = rapports_resp.data or []
                # Batch fetch related sentiers and users
                sentier_ids = sorted({r.get('sentier_id') for r in rapports if r.get('sentier_id')})
                user_ids = sorted({r.get('user_id') for r in rapports if r.get('user_id')})
                sentiers_map = {}
                users_map = {}
                if sentier_ids:
                    sresp = supabase.table('sentier').select('id, nom, region').in_('id', sentier_ids).execute()
                    for s in (sresp.data or []):
                        sentiers_map[s['id']] = s
                if user_ids:
                    uresp = supabase.table('user').select('id, nom').in_('id', user_ids).execute()
                    for u in (uresp.data or []):
                        users_map[u['id']] = u

                # Annotate rapports with heures and related names
                ann = []
                for r in rapports:
                    # compute heures approximated from date_rapport
                    heures = 0
                    try:
                        dt_str = r.get('date_rapport')
                        if dt_str:
                            # handle possible Z suffix
                            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                            heures = round((datetime.utcnow() - dt).total_seconds() / 3600)
                        else:
                            heures = 0
                    except Exception:
                        heures = 0
                    r['heures'] = heures
                    s = sentiers_map.get(r.get('sentier_id'))
                    u = users_map.get(r.get('user_id'))
                    if s:
                        r['sentier_nom'] = s.get('nom')
                        r['region'] = s.get('region')
                    if u:
                        r['user_nom'] = u.get('nom')
                    ann.append(r)
                rapports = ann

                # Stats via count
                s_count = supabase.table('sentier').select('id', count='exact').execute().count or 0
                u_count = supabase.table('user').select('id', count='exact').execute().count or 0
                r_count = supabase.table('rapport').select('id', count='exact').gt('date_expiration', now).execute().count or 0
                stats = {'sentiers_count': s_count, 'users_count': u_count, 'rapports_actifs_count': r_count}
            else:
                db = get_db()
                rapports = db.execute('''
                    SELECT r.*, s.nom as sentier_nom, s.region, u.nom as user_nom,
                           ROUND(EXTRACT(EPOCH FROM (NOW() - r.date_rapport))/3600) as heures
                    FROM rapport r
                    JOIN sentier s ON r.sentier_id = s.id
                    JOIN "user" u ON r.user_id = u.id
                    WHERE r.date_expiration > NOW()
                    ORDER BY r.date_rapport DESC
                    LIMIT 5
                ''').fetchall()
                stats = db.execute('''
                    SELECT
                        (SELECT COUNT(*) FROM sentier) AS sentiers_count,
                        (SELECT COUNT(*) FROM "user") AS users_count,
                        (SELECT COUNT(*) FROM rapport WHERE date_expiration > NOW()) AS rapports_actifs_count
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
