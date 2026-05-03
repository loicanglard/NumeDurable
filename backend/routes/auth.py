from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
import bcrypt
from datetime import datetime
from backend.db import get_db
from backend.models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/inscription', methods=['GET', 'POST'])
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

        erreurs = []
        if not nom:
            erreurs.append('Le nom est requis.')
        if not email or '@' not in email:
            erreurs.append('Email invalide.')
        if len(mdp) < 8:
            erreurs.append('Le mot de passe doit faire au moins 8 caractères.')
        if mdp != mdp_confirm:
            erreurs.append('Les mots de passe ne correspondent pas.')
        if niveau not in ('débutant', 'intermédiaire', 'expert'):
            erreurs.append('Niveau invalide.')

        if erreurs:
            for e in erreurs:
                flash(e, 'erreur')
            return render_template('auth/inscription.html',
                                   nom=nom, email=email, niveau=niveau, localisation=localisation)

        db = get_db()
        try:
            existant = db.execute('SELECT id FROM user WHERE email = ?', (email,)).fetchone()
            if existant:
                flash('Cet email est déjà utilisé.', 'erreur')
                return render_template('auth/inscription.html',
                                       nom=nom, email=email, niveau=niveau, localisation=localisation)

            mdp_hash = bcrypt.hashpw(mdp.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cur = db.execute(
                'INSERT INTO user (nom, email, mdp_hash, niveau, localisation, date_inscription) VALUES (?, ?, ?, ?, ?, ?)',
                (nom, email, mdp_hash, niveau, localisation or None, datetime.utcnow())
            )
            db.commit()
            
            # Connexion automatique après inscription
            user_row = db.execute('SELECT * FROM user WHERE id = ?', (cur.lastrowid,)).fetchone()
            if user_row:
                user = User(user_row)
                login_user(user)
                flash(f'Bienvenue parmi nous, {user.nom} ! Votre compte a été créé.', 'succes')
                return redirect(url_for('sentiers.index'))
            
            flash('Compte créé ! Veuillez vous connecter.', 'succes')
            return redirect(url_for('auth.connexion'))
            
        except Exception as e:
            if db: db.rollback()
            import sys
            print(f"CRASH INSCRIPTION: {str(e)}", file=sys.stderr)
            flash(f"Erreur lors de l'inscription : {str(e)}", 'erreur')
            return render_template('auth/inscription.html',
                                   nom=nom, email=email, niveau=niveau, localisation=localisation)

    return render_template('auth/inscription.html')


def is_safe_url(target):
    # Sécurité minimale : l'URL doit être relative (commence par /) et non externe
    from urllib.parse import urlparse, urljoin
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


@auth_bp.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if current_user.is_authenticated:
        return redirect(url_for('sentiers.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        mdp = request.form.get('mdp', '')

        db = get_db()
        row = db.execute('SELECT * FROM user WHERE email = ?', (email,)).fetchone()

        if row and bcrypt.checkpw(mdp.encode('utf-8'), row['mdp_hash'].encode('utf-8')):
            user = User(row)
            login_user(user, remember=bool(request.form.get('souvenir')))
            flash(f'Content de vous revoir, {user.nom} !', 'succes')
            
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('sentiers.index'))
        else:
            flash('Email ou mot de passe incorrect.', 'erreur')

    return render_template('auth/connexion.html')


@auth_bp.route('/deconnexion')
@login_required
def deconnexion():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))
