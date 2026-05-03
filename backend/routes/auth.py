from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
import bcrypt
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
            db.execute(
                'INSERT INTO user (nom, email, mdp_hash, niveau, localisation) VALUES (?, ?, ?, ?, ?)',
                (nom, email, mdp_hash, niveau, localisation or None)
            )
            db.commit()
            flash('Compte créé avec succès ! Vous pouvez vous connecter.', 'succes')
            return redirect(url_for('auth.connexion'))
        except Exception as e:
            if db: db.rollback()
            # Log de l'erreur pour le debug (visible dans les logs Vercel/console)
            import sys
            print(f"CRASH INSCRIPTION: {str(e)}", file=sys.stderr)
            flash(f"Erreur lors de l'inscription : {str(e)}", 'erreur')
            return render_template('auth/inscription.html',
                                   nom=nom, email=email, niveau=niveau, localisation=localisation)

    return render_template('auth/inscription.html')


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
            flash(f'Bienvenue, {user.nom} !', 'succes')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('sentiers.index'))
        else:
            flash('Email ou mot de passe incorrect.', 'erreur')

    return render_template('auth/connexion.html')


@auth_bp.route('/deconnexion')
@login_required
def deconnexion():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))
