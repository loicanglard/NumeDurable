from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from backend.db import get_db
from datetime import datetime, timedelta
import logging

from backend.constants import OBSTACLES, STATUTS, TYPES_PRATIQUE, FLASH_SUCCESS, FLASH_ERROR

# Configure logging for important actions
logger = logging.getLogger(__name__)
rapports_bp = Blueprint('rapports', __name__, url_prefix='/rapports')

OBSTACLES_POSSIBLES = OBSTACLES


@rapports_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau():
    sentier_id = request.args.get('sentier_id', type=int)
    db = get_db()
    sentier = db.execute('SELECT * FROM sentier WHERE id = ?', (sentier_id,)).fetchone() if sentier_id else None

    if request.method == 'POST':
        sentier_id = request.form.get('sentier_id', type=int)
        statut = request.form.get('statut', '')
        type_pratique = request.form.get('type_pratique', '')
        obstacles = ','.join(request.form.getlist('obstacles'))
        commentaire = request.form.get('commentaire', '').strip()

        erreurs = []
        if not sentier_id: erreurs.append('Sentier requis.')
        if statut not in STATUTS: erreurs.append('Statut invalide.')
        if type_pratique not in TYPES_PRATIQUE: erreurs.append('Type de pratique invalide.')
        

        if erreurs:
            for e in erreurs: flash(e, FLASH_ERROR)
            return redirect(request.referrer or url_for('sentiers.index'))

        now = datetime.utcnow()
        date_expiration = (now + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        db.execute(
            'INSERT INTO rapport (user_id, sentier_id, statut, type_pratique, obstacles, commentaire, date_expiration, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)',
            (current_user.id, sentier_id, statut, type_pratique, obstacles or None, commentaire or None, date_expiration, now, now)
        )
        db.commit()
        logger.info(f"Rapport créé par user {current_user.id} pour sentier {sentier_id}")
        flash('Rapport déposé ! Valide 7 jours.', FLASH_SUCCESS)
        return redirect(url_for('sentiers.detail', id=sentier_id))

    sentiers = db.execute('SELECT id, nom, region FROM sentier ORDER BY nom').fetchall()
    return render_template('rapports/form.html', sentier=sentier, sentiers=sentiers,
                           statuts=STATUTS, types_pratique=TYPES_PRATIQUE,
                           obstacles_possibles=OBSTACLES_POSSIBLES, mode='nouveau')


@rapports_bp.route('/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier(id):
    db = get_db()
    rapport = db.execute('SELECT * FROM rapport WHERE id = ?', (id,)).fetchone()
    if not rapport:
        flash('Rapport introuvable.', FLASH_ERROR)
        return redirect(url_for('sentiers.index'))
    if rapport['user_id'] != current_user.id and not current_user.is_admin:
        flash('Non autorisé.', FLASH_ERROR)
        return redirect(url_for('sentiers.detail', id=rapport['sentier_id']))

    if request.method == 'POST':
        statut = request.form.get('statut', '')
        type_pratique = request.form.get('type_pratique', '')
        obstacles = ','.join(request.form.getlist('obstacles'))
        commentaire = request.form.get('commentaire', '').strip()

        db.execute(
            'UPDATE rapport SET statut=?, type_pratique=?, obstacles=?, commentaire=?, updated_at=? WHERE id=?',
            (statut, type_pratique, obstacles or None, commentaire or None, datetime.utcnow(), id)
        )
        db.commit()
        flash('Rapport modifié.', FLASH_SUCCESS)
        return redirect(url_for('sentiers.detail', id=rapport['sentier_id']))

    sentier = db.execute('SELECT * FROM sentier WHERE id = ?', (rapport['sentier_id'],)).fetchone()
    obstacles_actifs = rapport['obstacles'].split(',') if rapport['obstacles'] else []
    return render_template('rapports/form.html', rapport=rapport, sentier=sentier,
                           statuts=STATUTS, types_pratique=TYPES_PRATIQUE,
                           obstacles_possibles=OBSTACLES_POSSIBLES,
                           obstacles_actifs=obstacles_actifs, mode='modifier')


@rapports_bp.route('/<int:id>/supprimer', methods=['POST'])
@login_required
def supprimer(id):
    db = get_db()
    rapport = db.execute('SELECT * FROM rapport WHERE id = ?', (id,)).fetchone()
    if not rapport:
        flash('Rapport introuvable.', FLASH_ERROR)
        return redirect(url_for('sentiers.index'))
    if rapport['user_id'] != current_user.id and not current_user.is_admin:
        flash('Non autorisé.', FLASH_ERROR)
        return redirect(url_for('sentiers.detail', id=rapport['sentier_id']))

    sentier_id = rapport['sentier_id']
    db.execute('DELETE FROM rapport WHERE id = ?', (id,))
    db.commit()
    flash('Rapport supprimé.', FLASH_SUCCESS)
    return redirect(url_for('sentiers.detail', id=sentier_id))
