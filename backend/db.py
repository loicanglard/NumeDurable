import sqlite3
import os
import click
import bcrypt
from datetime import datetime, timedelta
from flask import current_app, g


def _has_column(db, table_name, column_name):
    rows = db.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return any(row['name'] == column_name for row in rows)


def _ensure_audit_columns(db):
    """Crée les colonnes d'audit (created_at, updated_at) si absentes.
    
    Effectue une migration progressive : crée les colonnes, puis migre
    les données depuis les anciennes colonnes de date (date_inscription,
    date_ajout, date_rapport) pour garantir la continuité des données.
    """
    # Mapping table -> (audit_columns, source_column_for_legacy_data)
    table_mappings = {
        'user': (('created_at', 'updated_at'), 'date_inscription'),
        'sentier': (('created_at', 'updated_at'), 'date_ajout'),
        'rapport': (('created_at', 'updated_at'), 'date_rapport'),
    }
    
    for table_name, (columns, legacy_column) in table_mappings.items():
        # Ajouter les colonnes d'audit si manquantes
        for column_name in columns:
            if not _has_column(db, table_name, column_name):
                db.execute(f'ALTER TABLE "{table_name}" ADD COLUMN {column_name} DATETIME')
        
        # Migrer les données depuis les anciennes colonnes
        db.execute(f'''
            UPDATE "{table_name}"
            SET created_at = COALESCE(created_at, {legacy_column}),
                updated_at = COALESCE(updated_at, {legacy_column})
            WHERE created_at IS NULL OR updated_at IS NULL
        ''')


def _format_dt(value):
    return value.strftime('%Y-%m-%d %H:%M:%S')


def _seed_demo_data(db):
    """Insère des données de démonstration pour faciliter les tests.
    
    À utiliser uniquement en développement local. Ces données incluent :
    - 3 utilisateurs avec différents niveaux (débutant, intermédiaire, expert)
    - 6 sentiers variés (différentes régions, difficultés)
    - 8 rapports récents simulant l'activité
    
    Les données sont cohérentes : rapports avec des dates échelonnées
    pour montrer l'expiration après 7 jours.
    """
    now = datetime.utcnow()

    users = [
        (1, 'Alice Martin', 'alice@trail.fr', 'alice1234', 'expert', 'Chamonix', 1),
        (2, 'Nadia Laurent', 'nadia@trail.fr', 'nadia1234', 'intermédiaire', 'Grenoble', 0),
        (3, 'Marc Dubois', 'marc@trail.fr', 'marc1234', 'débutant', 'Annecy', 0),
    ]

    sentiers = [
        (1, 'Tour du Lac Blanc', 'Haute-Savoie', 11.8, 890, 'moyen', 'trail,rando', 'Alpin', 'Juin à Octobre', 'Boucle panoramique très fréquentée.', 1),
        (2, 'Crêtes de la Chartreuse', 'Isère', 18.4, 1260, 'difficile', 'trail,rando', 'Montagnard', 'Mai à Octobre', 'Crêtes exposées avec belles vues.', 2),
        (3, 'Forêt de Fontainebleau', 'Seine-et-Marne', 9.6, 180, 'facile', 'trail,vtt,rando', 'Forestier', 'Toute saison', 'Idéal pour les sorties courtes.', 3),
        (4, 'Belvédère des Aigles', 'Savoie', 14.2, 980, 'difficile', 'trail', 'Rocailleux', 'Juin à Septembre', 'Sentier technique avec passages engagés.', 1),
        (5, 'Lac des Miroirs', 'Hautes-Alpes', 7.5, 420, 'facile', 'rando', 'Alpin doux', 'Juin à Novembre', 'Promenade familiale autour du lac.', 2),
        (6, 'Traversée des Balcons', 'Drôme', 22.1, 1450, 'expert', 'trail,rando', 'Mixte', 'Juillet à Octobre', 'Longue traversée pour coureurs expérimentés.', 3),
    ]

    rapports = [
        (1, 1, 1, 'praticable', 'trail', 'sec,propre', 'Très bon état, quelques portions humides au lever du jour.', 0),
        (2, 2, 2, 'partiel', 'trail', 'boue,vent', 'Quelques zones boueuses sur les portions ombragées.', 1),
        (3, 3, 3, 'praticable', 'vtt', 'sec', 'Parcours roulant et agréable, parfait en VTT.', 2),
        (4, 1, 4, 'ferme', 'trail', 'arbre_tombe', 'Un arbre est tombé après la tempête, accès barré.', 0),
        (5, 2, 5, 'praticable', 'rando', 'sec', 'Vue dégagée, aucune difficulté particulière.', 1),
        (6, 3, 6, 'partiel', 'trail', 'neige,verglas', 'Neige persistante sur les crêtes, prudence nécessaire.', 2),
        (7, 1, 2, 'praticable', 'rando', 'sec', 'Sentier propre, balisage OK.', 3),
        (8, 2, 1, 'partiel', 'trail', 'boue', 'Terrain gras sur les 3 derniers kilomètres.', 4),
    ]

    for user_id, nom, email, password, niveau, localisation, is_admin in users:
        created_at = now - timedelta(days=user_id * 9)
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.execute(
            'INSERT INTO "user" (id, nom, email, mdp_hash, niveau, localisation, is_admin, date_inscription, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (user_id, nom, email, password_hash, niveau, localisation, is_admin, _format_dt(created_at), _format_dt(created_at), _format_dt(created_at))
        )

    for sentier_id, nom, region, distance_km, denivele_pos, difficulte, types_pratique, terrain, saison_recommandee, description, user_id in sentiers:
        created_at = now - timedelta(days=sentier_id * 3)
        db.execute(
            'INSERT INTO sentier (id, nom, region, distance_km, denivele_pos, difficulte, types_pratique, terrain, saison_recommandee, description, user_id, date_ajout, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (sentier_id, nom, region, distance_km, denivele_pos, difficulte, types_pratique, terrain, saison_recommandee, description, user_id, _format_dt(created_at), _format_dt(created_at), _format_dt(created_at))
        )

    for rapport_id, user_id, sentier_id, statut, type_pratique, obstacles, commentaire, age_days in rapports:
        date_rapport = now - timedelta(days=age_days, hours=rapport_id * 2)
        date_expiration = date_rapport + timedelta(days=7)
        db.execute(
            'INSERT INTO rapport (id, user_id, sentier_id, date_rapport, date_expiration, statut, type_pratique, obstacles, commentaire, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (rapport_id, user_id, sentier_id, _format_dt(date_rapport), _format_dt(date_expiration), statut, type_pratique, obstacles, commentaire, _format_dt(date_rapport), _format_dt(date_rapport))
        )

def get_db():
    if 'db' not in g:
        db_url = current_app.config['DATABASE']
        
        # S'assurer que le dossier existe
        db_dir = os.path.dirname(db_url)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        conn = sqlite3.connect(
            db_url,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('PRAGMA foreign_keys = ON')
        except sqlite3.Error:
            pass
        g.db = conn
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app):
    app.teardown_appcontext(close_db)
    
    with app.app_context():
        db_path = app.config.get('DATABASE')
        if db_path and (not os.path.exists(db_path) or os.path.getsize(db_path) == 0):
            try:
                db = get_db()
                with app.open_resource('database/schema.sql') as f:
                    db.executescript(f.read().decode('utf8'))
                _ensure_audit_columns(db)
                db.commit()
            except Exception as e:
                current_app.logger.exception('SQLite Init Error')

    @app.cli.command('init-db')
    def init_db_command():
        db = get_db()
        with current_app.open_resource('database/schema.sql') as f:
            db.executescript(f.read().decode('utf8'))
        click.echo('Base de données initialisée.')

    @app.cli.command('reset-db')
    def reset_db_command():
        db = get_db()
        db.execute('PRAGMA foreign_keys = OFF')
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        for table in tables:
            db.execute(f'DROP TABLE IF EXISTS {table["name"]}')
        db.execute('PRAGMA foreign_keys = ON')
        
        with current_app.open_resource('database/schema.sql') as f:
            db.executescript(f.read().decode('utf8'))
        click.echo('Base de données réinitialisée.')

    @app.cli.command('seed-db')
    @click.option('--reset', is_flag=True, help="Vide d'abord les tables avant de réinsérer les données de test.")
    def seed_db_command(reset):
        db = get_db()

        existing = db.execute('SELECT COUNT(*) AS total FROM sentier').fetchone()['total']
        if existing and not reset:
            click.echo('La base contient déjà des données. Utilise --reset pour repartir de zéro.')
            return

        db.execute('PRAGMA foreign_keys = OFF')
        db.execute('DELETE FROM rapport')
        db.execute('DELETE FROM sentier')
        db.execute('DELETE FROM "user"')
        try:
            db.execute("DELETE FROM sqlite_sequence WHERE name IN ('rapport', 'sentier', 'user')")
        except sqlite3.Error:
            pass
        db.execute('PRAGMA foreign_keys = ON')

        _ensure_audit_columns(db)
        _seed_demo_data(db)
        db.commit()

        click.echo('Base de données peuplée avec des données de test.')
        click.echo('Comptes de test :')
        click.echo(' - alice@trail.fr / alice1234')
        click.echo(' - nadia@trail.fr / nadia1234')
        click.echo(' - marc@trail.fr / marc1234')