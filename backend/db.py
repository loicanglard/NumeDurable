import os
import re
import sqlite3
from flask import current_app, g


# SQL adapter : convertit la syntaxe SQLite → PostgreSQL à la volée

def _adapt_sql(sql):
    sql = sql.replace('?', '%s')
    sql = re.sub(r"datetime\('now'\)", 'NOW()', sql, flags=re.IGNORECASE)
    sql = re.sub(
        r'ROUND\s*\(\s*\(julianday\s*\(\s*\'now\'\s*\)\s*-\s*julianday\s*\(([^)]+)\)\s*\)\s*\*\s*24\s*\)',
        r'ROUND(EXTRACT(EPOCH FROM (NOW() - \1)) / 3600)',
        sql, flags=re.IGNORECASE
    )
    return sql


# Wrappers PostgreSQL (psycopg2) — mimiquent l'interface sqlite3

class _PgRow(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class _PgCursor:
    def __init__(self, raw_cursor, lastrowid=None):
        self._cur = raw_cursor
        self.lastrowid = lastrowid

    def fetchone(self):
        row = self._cur.fetchone()
        return _PgRow(row) if row is not None else None

    def fetchall(self):
        return [_PgRow(r) for r in self._cur.fetchall()]

    def __iter__(self):
        return (_PgRow(r) for r in self._cur)

    def __getitem__(self, key):
        return self.fetchone()[key]


class _PgConn:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        sql = _adapt_sql(sql)
        is_insert = sql.strip().upper().startswith('INSERT')
        if is_insert and 'RETURNING' not in sql.upper():
            sql = sql.rstrip('; \n') + ' RETURNING id'

        cur = self._conn.cursor()
        cur.execute(sql, params if params else None)

        lastrowid = None
        if is_insert:
            row = cur.fetchone()
            lastrowid = _PgRow(row)['id'] if row else None

        return _PgCursor(cur, lastrowid)

    def executescript(self, script):
        cur = self._conn.cursor()
        for stmt in re.split(r';\s*\n', script):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                try:
                    cur.execute(stmt)
                except Exception:
                    pass
        self._conn.commit()
        cur.close()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


# API publique

def get_db():
    if 'db' not in g:
        database_url = current_app.config.get('DATABASE_URL')

        if database_url:
            import psycopg2
            import psycopg2.extras
            raw = psycopg2.connect(
                database_url,
                cursor_factory=psycopg2.extras.RealDictCursor,
                connect_timeout=10,
            )
            g.db = _PgConn(raw)
        else:
            db_path = current_app.config['DATABASE']
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
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
        database_url = app.config.get('DATABASE_URL')

        if database_url:
            schema_pg = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'database', 'schema_pg.sql'
            )
            if os.path.exists(schema_pg):
                try:
                    db = get_db()
                    with open(schema_pg, encoding='utf-8') as f:
                        db.executescript(f.read())
                except Exception as e:
                    print(f"PostgreSQL Init Error: {e}")
        else:
            db_path = app.config.get('DATABASE')
            if db_path and (not os.path.exists(db_path) or os.path.getsize(db_path) == 0):
                try:
                    db = get_db()
                    with app.open_resource('database/schema.sql') as f:
                        db.executescript(f.read().decode('utf8'))
                except Exception as e:
                    print(f"SQLite Init Error: {e}")