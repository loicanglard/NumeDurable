import sqlite3
import os
import click
from flask import current_app, g

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
            except Exception as e:
                print(f"SQLite Init Error: {e}")

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
