from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import bcrypt
from backend.db import get_db

users_bp = Blueprint('users', __name__, url_prefix='/utilisateurs')

NIVEAUX = ['débutant', 'intermédiaire', 'expert']


@users_bp.route('/profil')
@login_required
def profil():
    db = get_db()
    rapports = db.execute('''
        SELECT r.*, s.nom as sentier_nom FROM rapport r
        JOIN sentier s ON r.sentier_id = s.id
        WHERE r.user_id = ?
        ORDER BY r.date_rapport DESC LIMIT 10
    ''', (current_user.id,)).fetchall()
    sentiers = db.execute('SELECT * FROM sentier WHERE user_id = ? ORDER BY date_ajout DESC', (current_user.id,)).fetchall()
    return render_template('users/profil.html', rapports=rapports, sentiers=sentiers, niveaux=NIVEAUX)


@users_bp.route('/profil', methods=['POST'])
@login_required
def profil_modifier():
    db = get_db()
    nom = request.form.get('nom', '').strip()
    niveau = request.form.get('niveau', '')
    localisation = request.form.get('localisation', '').strip()
    mdp = request.form.get('mdp', '')
    mdp_confirm = request.form.get('mdp_confirm', '')

    erreurs = []
    if not nom: erreurs.append('Le nom est requis.')
    if niveau not in NIVEAUX: erreurs.append('Niveau invalide.')
    if mdp and len(mdp) < 8: erreurs.append('Mot de passe trop court (8 car. min).')
    if mdp and mdp != mdp_confirm: erreurs.append('Les mots de passe ne correspondent pas.')

    if erreurs:
        for e in erreurs: flash(e, 'erreur')
        return redirect(url_for('users.profil'))

    if mdp:
        now = datetime.utcnow()
        mdp_hash = bcrypt.hashpw(mdp.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.execute('UPDATE "user" SET nom=?, niveau=?, localisation=?, mdp_hash=?, updated_at=? WHERE id=?',
                   (nom, niveau, localisation or None, mdp_hash, now, current_user.id))
    else:
        db.execute('UPDATE "user" SET nom=?, niveau=?, localisation=?, updated_at=? WHERE id=?',
                   (nom, niveau, localisation or None, datetime.utcnow(), current_user.id))
    db.commit()
    flash('Profil mis à jour.', 'succes')
    return redirect(url_for('users.profil'))


@users_bp.route('/supprimer', methods=['POST'])
@login_required
def supprimer():
    db = get_db()
    db.execute('DELETE FROM "user" WHERE id = ?', (current_user.id,))
    db.commit()
    from flask_login import logout_user
    logout_user()
    flash('Votre compte a été supprimé.', 'info')
    return redirect(url_for('index'))


@users_bp.route('/<int:id>')
def public(id):
    db = get_db()
    user = db.execute('SELECT id, nom, niveau, localisation, date_inscription FROM "user" WHERE id = ?', (id,)).fetchone()
    if not user:
        flash('Utilisateur introuvable.', 'erreur')
        return redirect(url_for('sentiers.index'))
    rapports = db.execute('''
        SELECT r.*, s.nom as sentier_nom FROM rapport r
        JOIN sentier s ON r.sentier_id = s.id
        WHERE r.user_id = ? ORDER BY r.date_rapport DESC LIMIT 10
    ''', (id,)).fetchall()
    return render_template('users/public.html', profil=user, rapports=rapports)
