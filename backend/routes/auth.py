from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
import bcrypt
from datetime import datetime
from backend.db import get_db
from backend.models import User
from backend.constants import FLASH_SUCCESS, FLASH_ERROR, FLASH_INFO, get_limiter
from backend.validators import validate_user_signup

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
limiter = get_limiter()


@auth_bp.route('/inscription', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def inscription():
    if current_user.is_authenticated:
        return redirect(url_for('sentiers.index'))

    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        email = request.form.get('email', '').strip().lower()
        mdp = request.form.get('mdp', '')
        mdp_confirm = request.form.get('mdp_confirm', '')
        niveau = request.form.get('niveau', 'débutant')
        localisation = request.form.get('localisation', '').strip()

        # Valider les données (logique centralisée)
        form_data = {
            'nom': nom,
            'email': email,
            'mdp': mdp,
            'mdp_confirm': mdp_confirm,
            'niveau': niveau
        }
        is_valid, erreurs = validate_user_signup(form_data)
        
        if not is_valid:
            for e in erreurs:
                flash(e, FLASH_ERROR)
            return render_template('auth/inscription.html',
                                   nom=nom, email=email, niveau=niveau, localisation=localisation)

        supabase = current_app.supabase
        try:
            if supabase:
                exist_resp = supabase.table('user').select('id').eq('email', email).execute()
                if exist_resp.data:
                    flash('Cet email est déjà utilisé.', FLASH_ERROR)
                    return render_template('auth/inscription.html', nom=nom, email=email, niveau=niveau, localisation=localisation)

                mdp_hash = bcrypt.hashpw(mdp.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                now = datetime.utcnow()
                payload = {
                    'nom': nom,
                    'email': email,
                    'mdp_hash': mdp_hash,
                    'niveau': niveau,
                    'localisation': localisation or None,
                    'date_inscription': now.isoformat(),
                    'created_at': now.isoformat(),
                    'updated_at': now.isoformat()
                }
                ins = supabase.table('user').insert(payload).select('id').execute()
                user_id = ins.data[0]['id'] if (ins.data and len(ins.data) > 0) else None
                if user_id:
                    user_resp = supabase.table('user').select('*').eq('id', user_id).execute()
                    if user_resp.data:
                        user = User(user_resp.data[0])
                        login_user(user)
                        flash(f'Bienvenue parmi nous, {user.nom} ! Votre compte a été créé.', FLASH_SUCCESS)
                        return redirect(url_for('sentiers.index'))
                flash('Compte créé ! Veuillez vous connecter.', FLASH_SUCCESS)
                return redirect(url_for('auth.connexion'))
            else:
                db = get_db()
                existant = db.execute('SELECT id FROM "user" WHERE email = %s', (email,)).fetchone()
                if existant:
                    flash('Cet email est déjà utilisé.', FLASH_ERROR)
                    return render_template('auth/inscription.html', nom=nom, email=email, niveau=niveau, localisation=localisation)

                mdp_hash = bcrypt.hashpw(mdp.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                now = datetime.utcnow()
                cur = db.execute(
                    'INSERT INTO "user" (nom, email, mdp_hash, niveau, localisation, date_inscription, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id',
                    (nom, email, mdp_hash, niveau, localisation or None, now, now, now)
                ).fetchone()
                db.commit()

                user_row = db.execute('SELECT * FROM "user" WHERE id = %s', (cur['id'],)).fetchone()
                if user_row:
                    user = User(user_row)
                    login_user(user)
                    flash(f'Bienvenue parmi nous, {user.nom} ! Votre compte a été créé.', FLASH_SUCCESS)
                    return redirect(url_for('sentiers.index'))
                flash('Compte créé ! Veuillez vous connecter.', FLASH_SUCCESS)
                return redirect(url_for('auth.connexion'))
        except Exception:
            if not supabase:
                try:
                    db.rollback()
                except Exception:
                    pass
            current_app.logger.exception("Erreur lors de l'inscription")
            flash('Erreur lors de l\'inscription. Veuillez réessayer plus tard.', FLASH_ERROR)
            return render_template('auth/inscription.html', nom=nom, email=email, niveau=niveau, localisation=localisation)

    return render_template('auth/inscription.html')


def is_safe_url(target):
    # Sécurité minimale : l'URL doit être relative (commence par /) et non externe
    from urllib.parse import urlparse, urljoin
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


@auth_bp.route('/connexion', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def connexion():
    if current_user.is_authenticated:
        return redirect(url_for('sentiers.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        mdp = request.form.get('mdp', '')

        supabase = current_app.supabase
        row = None
        if supabase:
            resp = supabase.table('user').select('*').eq('email', email).execute()
            row = resp.data[0] if (resp.data and len(resp.data) > 0) else None
        else:
            db = get_db()
            row = db.execute('SELECT * FROM "user" WHERE email = %s', (email,)).fetchone()

        if row and bcrypt.checkpw(mdp.encode('utf-8'), row['mdp_hash'].encode('utf-8')):
            user = User(row)
            login_user(user, remember=True)
            
            flash(f'Content de vous revoir, {user.nom} !', FLASH_SUCCESS)
            
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('sentiers.index'))
        else:
            flash('Email ou mot de passe incorrect.', FLASH_ERROR)

    return render_template('auth/connexion.html')


@auth_bp.route('/deconnexion')
@login_required
def deconnexion():
    logout_user()
    flash('Vous avez été déconnecté.', FLASH_INFO)
    return redirect(url_for('index'))
