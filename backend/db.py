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
        
        # Sur Vercel, si le fichier SQLite n'existe pas dans /tmp, on doit l'initialiser
        if db_type == 'sqlite' and current_app.config.get('IS_SERVERLESS'):
            if not os.path.exists(db_url):
                # On s'assure que le dossier parent existe
                os.makedirs(os.path.dirname(db_url), exist_ok=True)
                # On force l'initialisation du schéma
                with current_app.open_resource('database/schema.sql') as f:
                    conn = sqlite3.connect(db_url)
                    conn.executescript(f.read().decode('utf8'))
                    conn.close()

        if db_type == 'postgres':
            if psycopg2:
                try:
                    conn = psycopg2.connect(db_url)
                    g.db = PostgresWrapper(conn)
                    return g.db
                except Exception as e:
                    print(f"Error connecting to PostgreSQL: {e}")
                    raise
            else:
                # Si on est en local et que psycopg2 manque, on pourrait vouloir basculer sur SQLite
                # mais SURTOUT pas avec l'URL Postgres !
                if db_url.startswith(('postgresql://', 'postgres://')):
                    print("CRITICAL: DATABASE_URL is Postgres but 'psycopg2' is not installed.")
                    print("Fallback to SQLite (local file) for development.")
                    # Force local SQLite path for fallback
                    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
                    db_url = os.path.join(basedir, 'database', 'trailmemoire.db')
                    db_type = 'sqlite'
                else:
                    raise ImportError("psycopg2 is required for PostgreSQL connections.")

        if db_type == 'sqlite':
            # On s'assure que le dossier existe
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
            g.db = SQLiteWrapper(conn)
            
    return g.db

class SQLiteWrapper:
    """Wrapper pour SQLite gérant la compatibilité des noms de tables (users/user)"""
    def __init__(self, conn):
        self.conn = conn
        # On vérifie quelle table existe
        try:
            res = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
            self.has_users_table = res is not None
        except Exception:
            self.has_users_table = False

    def __getattr__(self, name):
        return getattr(self.conn, name)

    def execute(self, sql, params=()):
        # Si on a l'ancienne table 'user' mais que le code demande 'users'
        if not self.has_users_table and 'users' in sql.lower():
            # Remplacement intelligent de users par "user" (mot réservé)
            import re
            sql = re.sub(r'\busers\b', '"user"', sql, flags=re.IGNORECASE)
        return self.conn.execute(sql, params)

    def executescript(self, sql):
        return self.conn.executescript(sql)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

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
                    
                    # Traduction robuste SQLite -> Postgres
                    replacements = {
                        'INTEGER PRIMARY KEY AUTOINCREMENT': 'SERIAL PRIMARY KEY',
                        'DATETIME': 'TIMESTAMP',
                        'BOOLEAN DEFAULT 0': 'BOOLEAN DEFAULT FALSE',
                        'BOOLEAN DEFAULT 1': 'BOOLEAN DEFAULT TRUE',
                        'PRAGMA foreign_keys = ON;': '',
                        # Gestion des booléens dans les inserts
                        ', 1)': ', TRUE)',
                        ', 0)': ', FALSE)'
                    }
                    for old, new in replacements.items():
                        schema_sql = schema_sql.replace(old, new)
                    
                    # Nettoyage des commentaires et split par point-virgule
                    statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
                    
                    cur = db.conn.cursor()
                    for statement in statements:
                        try:
                            # On ignore les erreurs sur les index qui existent déjà (si IF NOT EXISTS échoue)
                            cur.execute(statement)
                        except Exception as e:
                            if "already exists" not in str(e).lower():
                                print(f"Warning during Postgres Init: {e}")
                    db.conn.commit()
            except Exception as e:
                print(f"Postgres Auto-Init Critical Error: {e}")

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
