import sqlite3
import os
import click
from flask import current_app, g

# Support PostgreSQL optionnel
try:
    import psycopg2
    from psycopg2.extras import DictCursor
except ImportError:
    psycopg2 = None

def get_db():
    if 'db' not in g:
        db_type = current_app.config.get('DB_TYPE', 'sqlite')
        db_url = current_app.config['DATABASE']
        
        if db_type == 'postgres' and psycopg2:
            conn = psycopg2.connect(db_url)
            g.db = PostgresWrapper(conn)
        else:
            # SQLite par défaut
            g.db = sqlite3.connect(
                db_url,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row
            try:
                g.db.execute('PRAGMA foreign_keys = ON')
            except sqlite3.Error:
                pass
    return g.db

class PostgresWrapper:
    """Wrapper pour simuler l'API sqlite3 avec psycopg2"""
    def __init__(self, conn):
        self.conn = conn

    def __getattr__(self, name):
        return getattr(self.conn, name)

    def execute(self, sql, params=()):
        # Traduction plus robuste SQL
        sql_clean = sql.replace('?', '%s')
        sql_clean = sql_clean.replace("datetime('now')", "CURRENT_TIMESTAMP")
        
        # Gestion multi-ligne et espaces pour les calculs de dates
        import re
        sql_clean = re.sub(r"ROUND\(\(julianday\('now'\)\s*-\s*julianday\((.*?)\)\)\s*\*\s*24\)", 
                           r"ROUND(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - \1)) / 3600)", sql_clean, flags=re.IGNORECASE)
        sql_clean = re.sub(r"julianday\('now'\)", "EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)/86400", sql_clean, flags=re.IGNORECASE)

        is_insert = sql_clean.strip().upper().startswith('INSERT')
        if is_insert and 'RETURNING' not in sql_clean.upper():
            sql_clean += ' RETURNING id'

        cur = self.conn.cursor(cursor_factory=DictCursor)
        cur.execute(sql_clean, params)
        
        if is_insert:
            try:
                row = cur.fetchone()
                # On attache lastrowid au curseur pour simuler sqlite3
                cur.lastrowid = row[0] if row else None
            except Exception:
                cur.lastrowid = None
        return cur

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app):
    app.teardown_appcontext(close_db)
    
    with app.app_context():
        db_type = app.config.get('DB_TYPE', 'sqlite')
        db_path = app.config.get('DATABASE')
        
        # En SQLite, on initialise si le fichier est manquant
        if db_type == 'sqlite':
            if db_path and (not os.path.exists(db_path) or os.path.getsize(db_path) == 0):
                try:
                    db = get_db()
                    with app.open_resource('database/schema.sql') as f:
                        db.executescript(f.read().decode('utf8'))
                except Exception as e:
                    print(f"SQLite Init Error: {e}")
        
        # En Postgres, on tente une initialisation silencieuse (les tables ont IF NOT EXISTS)
        elif db_type == 'postgres':
            try:
                db = get_db()
                with app.open_resource('database/schema.sql') as f:
                    schema_sql = f.read().decode('utf8')
                    # Traduction à la volée du schéma SQLite vers Postgres
                    schema_sql = schema_sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
                    schema_sql = schema_sql.replace('DATETIME', 'TIMESTAMP')
                    schema_sql = schema_sql.replace('BOOLEAN DEFAULT 0', 'BOOLEAN DEFAULT FALSE')
                    schema_sql = schema_sql.replace('PRAGMA foreign_keys = ON;', '')
                    
                    cur = db.conn.cursor()
                    cur.execute(schema_sql)
                    db.conn.commit()
            except Exception as e:
                print(f"Postgres Auto-Init Error: {e}")

    @app.cli.command('init-db')
    def init_db_command():
        db = get_db()
        db_type = current_app.config.get('DB_TYPE', 'sqlite')
        with current_app.open_resource('database/schema.sql') as f:
            sql = f.read().decode('utf8')
            if db_type == 'sqlite':
                db.executescript(sql)
            else:
                sql = sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
                sql = sql.replace('DATETIME', 'TIMESTAMP')
                sql = sql.replace('BOOLEAN DEFAULT 0', 'BOOLEAN DEFAULT FALSE')
                cur = db.conn.cursor()
                cur.execute(sql)
                db.conn.commit()
        click.echo('Base de données initialisée.')

    @app.cli.command('reset-db')
    def reset_db_command():
        db = get_db()
        db_type = current_app.config.get('DB_TYPE', 'sqlite')
        
        if db_type == 'sqlite':
            db.execute('PRAGMA foreign_keys = OFF')
            tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
            for table in tables:
                db.execute(f'DROP TABLE IF EXISTS {table["name"]}')
            db.execute('PRAGMA foreign_keys = ON')
        else:
            cur = db.conn.cursor()
            cur.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'")
            tables = cur.fetchall()
            for table in tables:
                cur.execute(f'DROP TABLE IF EXISTS {table[0]} CASCADE')
            db.conn.commit()
        
        # Ré-initialisation
        with current_app.open_resource('database/schema.sql') as f:
            sql = f.read().decode('utf8')
            if db_type == 'sqlite':
                db.executescript(sql)
            else:
                sql = sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
                sql = sql.replace('DATETIME', 'TIMESTAMP')
                sql = sql.replace('BOOLEAN DEFAULT 0', 'BOOLEAN DEFAULT FALSE')
                cur = db.conn.cursor()
                cur.execute(sql)
                db.conn.commit()
        click.echo('Base de données réinitialisée.')
