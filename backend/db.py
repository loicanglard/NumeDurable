import os
import click
import bcrypt
from datetime import datetime, timedelta
from flask import current_app, g
from backend.supabase_utils import user_table

import psycopg2
import psycopg2.extras


class PGCursorWrapper:
    def __init__(self, cur):
        self._cur = cur

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __getattr__(self, name):
        return getattr(self._cur, name)


class PGConnectionWrapper:
    """Thin wrapper around psycopg2 connection providing a convenience
    `execute(sql, params)` which returns a cursor-like object with
    `fetchone()` / `fetchall()` similar to the previous sqlite API.
    """
    def __init__(self, conn):
        self._conn = conn

    def cursor(self, *args, **kwargs):
        return self._conn.cursor(*args, cursor_factory=psycopg2.extras.RealDictCursor, **kwargs)

    def execute(self, sql, params=None):
        if params is None:
            params = ()
        # allow existing code to use '?' placeholders -> convert to %s
        sql_pg = sql.replace('?', '%s')
        cur = self.cursor()
        cur.execute(sql_pg, params)
        return PGCursorWrapper(cur)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        try:
            return self._conn.close()
        except Exception:
            pass


def _ensure_audit_columns(db):
    """Ensure `created_at` and `updated_at` exist on core tables and try
    to migrate legacy date columns if present. PostgreSQL-only.
    """
    table_mappings = {
        'user': (('created_at', 'updated_at'), 'date_inscription'),
        'sentier': (('created_at', 'updated_at'), 'date_ajout'),
        'rapport': (('created_at', 'updated_at'), 'date_rapport'),
    }

    for table_name, (columns, legacy_column) in table_mappings.items():
        for column_name in columns:
            try:
                db.execute(f'ALTER TABLE "{table_name}" ADD COLUMN {column_name} TIMESTAMP')
                db.commit()
            except Exception:
                db.rollback()

        try:
            db.execute(f'''
                UPDATE "{table_name}"
                SET created_at = COALESCE(created_at, "{legacy_column}"),
                    updated_at = COALESCE(updated_at, "{legacy_column}")
                WHERE created_at IS NULL OR updated_at IS NULL
            ''')
            db.commit()
        except Exception:
            db.rollback()


def _format_dt(value):
    return value.strftime('%Y-%m-%d %H:%M:%S')


def _seed_demo_data(db):
    """Seed demo data (PostgreSQL-only)."""
    now = datetime.utcnow()

    users = [
        ('Alice Martin', 'alice@trail.fr', 'alice1234', 'expert', 'Chamonix', True),
        ('Nadia Laurent', 'nadia@trail.fr', 'nadia1234', 'intermédiaire', 'Grenoble', False),
        ('Marc Dubois', 'marc@trail.fr', 'marc1234', 'débutant', 'Annecy', False),
    ]

    sentiers = [
        ('Tour du Lac Blanc', 'Haute-Savoie', 11.8, 890, 'moyen', 'trail,rando', 'Alpin', 'Juin à Octobre', 'Boucle panoramique très fréquentée.', 1),
        ('Crêtes de la Chartreuse', 'Isère', 18.4, 1260, 'difficile', 'trail,rando', 'Montagnard', 'Mai à Octobre', 'Crêtes exposées avec belles vues.', 2),
        ('Forêt de Fontainebleau', 'Seine-et-Marne', 9.6, 180, 'facile', 'trail,vtt,rando', 'Forestier', 'Toute saison', 'Idéal pour les sorties courtes.', 3),
        ('Belvédère des Aigles', 'Savoie', 14.2, 980, 'difficile', 'trail', 'Rocailleux', 'Juin à Septembre', 'Sentier technique avec passages engagés.', 1),
        ('Lac des Miroirs', 'Hautes-Alpes', 7.5, 420, 'facile', 'rando', 'Alpin doux', 'Juin à Novembre', 'Promenade familiale autour du lac.', 2),
        ('Traversée des Balcons', 'Drôme', 22.1, 1450, 'expert', 'trail,rando', 'Mixte', 'Juillet à Octobre', 'Longue traversée pour coureurs expérimentés.', 3),
    ]

    rapports = [
        (1, 1, 'praticable', 'trail', 'sec,propre', 'Très bon état, quelques portions humides au lever du jour.', 0),
        (2, 2, 'partiel', 'trail', 'boue,vent', 'Quelques zones boueuses sur les portions ombragées.', 1),
        (3, 3, 'praticable', 'vtt', 'sec', 'Parcours roulant et agréable, parfait en VTT.', 2),
        (1, 4, 'ferme', 'trail', 'arbre_tombe', 'Un arbre est tombé après la tempête, accès barré.', 0),
        (2, 5, 'praticable', 'rando', 'sec', 'Vue dégagée, aucune difficulté particulière.', 1),
        (3, 6, 'partiel', 'trail', 'neige,verglas', 'Neige persistante sur les crêtes, prudence nécessaire.', 2),
        (1, 2, 'praticable', 'rando', 'sec', 'Sentier propre, balisage OK.', 3),
        (2, 1, 'partiel', 'trail', 'boue', 'Terrain gras sur les 3 derniers kilomètres.', 4),
    ]

    try:
        # Insert users
        for nom, email, password, niveau, localisation, is_admin in users:
            created_at = now
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.execute(
                'INSERT INTO "user" (nom, email, mdp_hash, niveau, localisation, is_admin, date_inscription, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (nom, email, password_hash, niveau, localisation, is_admin, _format_dt(created_at), _format_dt(created_at), _format_dt(created_at))
            )

        # Insert sentiers
        for nom, region, distance_km, denivele_pos, difficulte, types_pratique, terrain, saison_recommandee, description, user_id in sentiers:
            created_at = now
            db.execute(
                'INSERT INTO sentier (nom, region, distance_km, denivele_pos, difficulte, types_pratique, terrain, saison_recommandee, description, user_id, date_ajout, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (nom, region, distance_km, denivele_pos, difficulte, types_pratique, terrain, saison_recommandee, description, user_id, _format_dt(created_at), _format_dt(created_at), _format_dt(created_at))
            )

        # Insert rapports
        for user_id, sentier_id, statut, type_pratique, obstacles, commentaire, age_days in rapports:
            date_rapport = now - timedelta(days=age_days)
            date_expiration = date_rapport + timedelta(days=7)
            db.execute(
                'INSERT INTO rapport (user_id, sentier_id, date_rapport, date_expiration, statut, type_pratique, obstacles, commentaire, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (user_id, sentier_id, _format_dt(date_rapport), _format_dt(date_expiration), statut, type_pratique, obstacles, commentaire, _format_dt(date_rapport), _format_dt(date_rapport))
            )

        db.commit()
    except Exception as e:
        current_app.logger.exception(f'Seed data error: {e}')
        db.rollback()
        raise


def _seed_demo_data_supabase(supabase):
    """Seed demo data using Supabase REST API."""
    now = datetime.utcnow()

    users = [
        ('Alice Martin', 'alice@trail.fr', 'alice1234', 'expert', 'Chamonix', True),
        ('Nadia Laurent', 'nadia@trail.fr', 'nadia1234', 'intermédiaire', 'Grenoble', False),
        ('Marc Dubois', 'marc@trail.fr', 'marc1234', 'débutant', 'Annecy', False),
    ]

    sentiers = [
        ('Tour du Lac Blanc', 'Haute-Savoie', 11.8, 890, 'moyen', 'trail,rando', 'Alpin', 'Juin à Octobre', 'Boucle panoramique très fréquentée.', 1),
        ('Crêtes de la Chartreuse', 'Isère', 18.4, 1260, 'difficile', 'trail,rando', 'Montagnard', 'Mai à Octobre', 'Crêtes exposées avec belles vues.', 2),
        ('Forêt de Fontainebleau', 'Seine-et-Marne', 9.6, 180, 'facile', 'trail,vtt,rando', 'Forestier', 'Toute saison', 'Idéal pour les sorties courtes.', 3),
        ('Belvédère des Aigles', 'Savoie', 14.2, 980, 'difficile', 'trail', 'Rocailleux', 'Juin à Septembre', 'Sentier technique avec passages engagés.', 1),
        ('Lac des Miroirs', 'Hautes-Alpes', 7.5, 420, 'facile', 'rando', 'Alpin doux', 'Juin à Novembre', 'Promenade familiale autour du lac.', 2),
        ('Traversée des Balcons', 'Drôme', 22.1, 1450, 'expert', 'trail,rando', 'Mixte', 'Juillet à Octobre', 'Longue traversée pour coureurs expérimentés.', 3),
    ]

    rapports = [
        (1, 1, 'praticable', 'trail', 'sec,propre', 'Très bon état, quelques portions humides au lever du jour.', 0),
        (2, 2, 'partiel', 'trail', 'boue,vent', 'Quelques zones boueuses sur les portions ombragées.', 1),
        (3, 3, 'praticable', 'vtt', 'sec', 'Parcours roulant et agréable, parfait en VTT.', 2),
        (1, 4, 'ferme', 'trail', 'arbre_tombe', 'Un arbre est tombé après la tempête, accès barré.', 0),
        (2, 5, 'praticable', 'rando', 'sec', 'Vue dégagée, aucune difficulté particulière.', 1),
        (3, 6, 'partiel', 'trail', 'neige,verglas', 'Neige persistante sur les crêtes, prudence nécessaire.', 2),
        (1, 2, 'praticable', 'rando', 'sec', 'Sentier propre, balisage OK.', 3),
        (2, 1, 'partiel', 'trail', 'boue', 'Terrain gras sur les 3 derniers kilomètres.', 4),
    ]

    # Keep insertion order IDs mapping for demo tuples.
    user_ids = []
    sentier_ids = []

    ut = user_table(supabase)

    for nom, email, password, niveau, localisation, is_admin in users:
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        payload = {
            'nom': nom,
            'email': email,
            'mdp_hash': password_hash,
            'niveau': niveau,
            'localisation': localisation,
            'is_admin': is_admin,
            'date_inscription': now.isoformat(),
        }
        ins = ut.insert(payload).select('id,email').execute()
        if ins.data:
            user_ids.append(ins.data[0]['id'])
        else:
            fetched = ut.select('id').eq('email', email).limit(1).execute()
            if not fetched.data:
                raise RuntimeError(f'Unable to retrieve inserted user id for {email}')
            user_ids.append(fetched.data[0]['id'])

    for nom, region, distance_km, denivele_pos, difficulte, types_pratique, terrain, saison_recommandee, description, user_index in sentiers:
        payload = {
            'nom': nom,
            'region': region,
            'distance_km': distance_km,
            'denivele_pos': denivele_pos,
            'difficulte': difficulte,
            'types_pratique': types_pratique,
            'terrain': terrain,
            'saison_recommandee': saison_recommandee,
            'description': description,
            'user_id': user_ids[user_index - 1],
            'date_ajout': now.isoformat(),
        }
        ins = supabase.table('sentier').insert(payload).select('id').execute()
        if not ins.data:
            raise RuntimeError(f'Unable to retrieve inserted sentier id for {nom}')
        sentier_ids.append(ins.data[0]['id'])

    for user_index, sentier_index, statut, type_pratique, obstacles, commentaire, age_days in rapports:
        date_rapport = now - timedelta(days=age_days)
        date_expiration = date_rapport + timedelta(days=7)
        payload = {
            'user_id': user_ids[user_index - 1],
            'sentier_id': sentier_ids[sentier_index - 1],
            'date_rapport': date_rapport.isoformat(),
            'date_expiration': date_expiration.isoformat(),
            'statut': statut,
            'type_pratique': type_pratique,
            'obstacles': obstacles,
            'commentaire': commentaire,
        }
        supabase.table('rapport').insert(payload).execute()


def get_db():
    """Return a PostgreSQL connection wrapper stored on `g`.

    Expects `current_app.config['DATABASE']` to contain the full
    connection URL (e.g. Supabase `DATABASE_URL`).
    """
    if 'db' not in g:
        db_url = current_app.config['DATABASE']
        try:
            # Try a short connect timeout and require SSL (Supabase needs SSL).
            conn = psycopg2.connect(db_url, connect_timeout=10, sslmode='require')
        except Exception as e:
            # Provide a clearer message for common connectivity issues.
            current_app.logger.exception(f'Database connection failed: {e}')
            hint = (
                'Unable to connect to the PostgreSQL host.\n'
                '- Check that your INTERNET and network allow outbound TCP port 5432.\n'
                '- If you are behind a firewall, VPN, or proxy, try disabling it temporarily.\n'
                '- Ensure the `DATABASE_URL` in your .env is correct and includes `?sslmode=require` if needed.\n'
                "- From this machine try: `psql '<DATABASE_URL>'` or `telnet <host> 5432` to verify connectivity."
            )
            raise RuntimeError(f'Database connection failed: {e}\n{hint}') from e

        g.db = PGConnectionWrapper(conn)
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass


def init_db(app):
    """Register teardown and CLI commands (PostgreSQL-only)."""
    app.teardown_appcontext(close_db)

    @app.cli.command('init-db')
    def init_db_command():
        """Initialize PostgreSQL schema from `database/schema_postgresql.sql`."""
        db = get_db()
        try:
            with current_app.open_resource('database/schema_postgresql.sql') as f:
                sql = f.read().decode('utf8')
                cur = db.cursor()
                cur.execute(sql)
                db.commit()
            click.echo('PostgreSQL schema initialized.')
        except Exception as e:
            current_app.logger.exception(f'Init DB Error: {e}')
            click.echo(f'Error: {e}', err=True)

    @app.cli.command('reset-db')
    def reset_db_command():
        """Drop tables and recreate schema."""
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('''
                DROP TABLE IF EXISTS rapport CASCADE;
                DROP TABLE IF EXISTS sentier CASCADE;
                DROP TABLE IF EXISTS "user" CASCADE;
            ''')
            db.commit()
            with current_app.open_resource('database/schema_postgresql.sql') as f:
                cur.execute(f.read().decode('utf8'))
                db.commit()
            click.echo('PostgreSQL database reset.')
        except Exception as e:
            current_app.logger.exception(f'Reset DB Error: {e}')
            click.echo(f'Error: {e}', err=True)

    @app.cli.command('seed-db')
    @click.option('--reset', is_flag=True, help="Reset database before seeding.")
    def seed_db_command(reset):
        try:
            supabase = getattr(current_app, 'supabase', None)

            # For seeding, prefer a service role key when provided so RLS does not block inserts.
            service_role_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
            supabase_url = os.environ.get('SUPABASE_URL') or current_app.config.get('SUPABASE_URL')
            if service_role_key and supabase_url:
                from supabase import create_client
                supabase = create_client(supabase_url, service_role_key)

            if supabase:
                existing_rows = supabase.table('sentier').select('id').limit(1).execute().data or []
                if existing_rows and not reset:
                    click.echo('Database already contains data. Use --reset to clear first.')
                    return

                if reset:
                    # Respect FK order: rapports -> sentiers -> users.
                    supabase.table('rapport').delete().neq('id', 0).execute()
                    supabase.table('sentier').delete().neq('id', 0).execute()
                    user_table(supabase).delete().neq('id', 0).execute()

                _seed_demo_data_supabase(supabase)
            else:
                db = get_db()
                cur = db.execute('SELECT COUNT(*) AS total FROM sentier')
                existing = cur.fetchone()[0]
                if existing and not reset:
                    click.echo('Database already contains data. Use --reset to clear first.')
                    return

                cur = db.cursor()
                cur.execute('DELETE FROM rapport')
                cur.execute('DELETE FROM sentier')
                cur.execute('DELETE FROM "user"')
                db.commit()

                _ensure_audit_columns(db)
                _seed_demo_data(db)

            click.echo('Database seeded with demo data.')
            click.echo('Test accounts:')
            click.echo(' - alice@trail.fr / alice1234')
            click.echo(' - nadia@trail.fr / nadia1234')
            click.echo(' - marc@trail.fr / marc1234')
        except Exception as e:
            message = str(e)
            if 'row-level security policy' in message.lower() or "'code': '42501'" in message:
                click.echo('RLS bloque le seed via la clé Supabase actuelle.', err=True)
                click.echo('Ajoute SUPABASE_SERVICE_ROLE_KEY dans ton .env puis relance seed-db.', err=True)
                click.echo('Exemple: SUPABASE_SERVICE_ROLE_KEY=eyJ... (service_role key du dashboard Supabase)', err=True)
            current_app.logger.exception(f'Seed DB Error: {e}')
            click.echo(f'Error: {e}', err=True)