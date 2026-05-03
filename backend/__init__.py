import os
from datetime import datetime
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from backend.db import init_db, get_db

def create_app():
    # On définit le chemin racine vers le dossier parent de 'backend'
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    app = Flask(
        __name__,
        template_folder=os.path.join(root_path, 'frontend/templates'),
        static_folder=os.path.join(root_path, 'frontend/static'),
        root_path=root_path
    )
    app.config.from_object('config.Config')

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

    @login_manager.user_loader
    def load_user(user_id):
        db = get_db()
        row = db.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
        return User(row) if row else None

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(sentiers_bp)
    app.register_blueprint(rapports_bp)

    @app.route('/')
    def index():
        db = get_db()
        rapports = db.execute('''
            SELECT r.*, s.nom as sentier_nom, s.region, u.nom as user_nom,
                   ROUND((julianday('now') - julianday(r.date_rapport)) * 24) as heures
            FROM rapport r
            JOIN sentier s ON r.sentier_id = s.id
            JOIN user u ON r.user_id = u.id
            WHERE r.date_expiration > datetime('now')
            ORDER BY r.date_rapport DESC
            LIMIT 5
        ''').fetchall()

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
