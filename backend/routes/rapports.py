from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
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
    supabase = current_app.supabase
    sentier = None
    if sentier_id and supabase:
        sresp = supabase.table('sentier').select('*').eq('id', sentier_id).execute()
        sentier = sresp.data[0] if (sresp.data and len(sresp.data) > 0) else None

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
        date_expiration = now + timedelta(days=7)
        if supabase:
            payload = {
                'user_id': current_user.id,
                'sentier_id': sentier_id,
                'statut': statut,
                'type_pratique': type_pratique,
                'obstacles': obstacles or None,
                'commentaire': commentaire or None,
                'date_expiration': date_expiration.isoformat(),
                'created_at': now.isoformat(),
                'updated_at': now.isoformat()
            }
            supabase.table('rapport').insert(payload).execute()
        else:
            db = get_db()
            db.execute(
                'INSERT INTO rapport (user_id, sentier_id, statut, type_pratique, obstacles, commentaire, date_expiration, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (current_user.id, sentier_id, statut, type_pratique, obstacles or None, commentaire or None, date_expiration, now, now)
            )
            db.commit()
        logger.info(f"Rapport créé par user {current_user.id} pour sentier {sentier_id}")
        flash('Rapport déposé ! Valide 7 jours.', FLASH_SUCCESS)
        return redirect(url_for('sentiers.detail', id=sentier_id))

    if supabase:
        sresp = supabase.table('sentier').select('id, nom, region').order('nom', desc=False).execute()
        sentiers = sresp.data or []
    else:
        db = get_db()
        sentiers = db.execute('SELECT id, nom, region FROM sentier ORDER BY nom').fetchall()
    return render_template('rapports/form.html', sentier=sentier, sentiers=sentiers,
                           statuts=STATUTS, types_pratique=TYPES_PRATIQUE,
                           obstacles_possibles=OBSTACLES_POSSIBLES, mode='nouveau')


@rapports_bp.route('/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier(id):
    supabase = current_app.supabase
    if supabase:
        rresp = supabase.table('rapport').select('*').eq('id', id).execute()
        rapport = rresp.data[0] if (rresp.data and len(rresp.data) > 0) else None
    else:
        db = get_db()
        rapport = db.execute('SELECT * FROM rapport WHERE id = %s', (id,)).fetchone()
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

        if supabase:
            supabase.table('rapport').update({
                'statut': statut,
                'type_pratique': type_pratique,
                'obstacles': obstacles or None,
                'commentaire': commentaire or None,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', id).execute()
        else:
            db.execute(
                'UPDATE rapport SET statut=%s, type_pratique=%s, obstacles=%s, commentaire=%s, updated_at=%s WHERE id=%s',
                (statut, type_pratique, obstacles or None, commentaire or None, datetime.utcnow(), id)
            )
            db.commit()
        flash('Rapport modifié.', FLASH_SUCCESS)
        return redirect(url_for('sentiers.detail', id=rapport['sentier_id']))

    if supabase:
        sresp = supabase.table('sentier').select('*').eq('id', rapport['sentier_id']).execute()
        sentier = sresp.data[0] if (sresp.data and len(sresp.data) > 0) else None
    else:
        sentier = db.execute('SELECT * FROM sentier WHERE id = %s', (rapport['sentier_id'],)).fetchone()
    obstacles_actifs = rapport['obstacles'].split(',') if rapport['obstacles'] else []
    return render_template('rapports/form.html', rapport=rapport, sentier=sentier,
                           statuts=STATUTS, types_pratique=TYPES_PRATIQUE,
                           obstacles_possibles=OBSTACLES_POSSIBLES,
                           obstacles_actifs=obstacles_actifs, mode='modifier')


@rapports_bp.route('/<int:id>/supprimer', methods=['POST'])
@login_required
def supprimer(id):
    supabase = current_app.supabase
    if supabase:
        rresp = supabase.table('rapport').select('*').eq('id', id).execute()
        rapport = rresp.data[0] if (rresp.data and len(rresp.data) > 0) else None
    else:
        db = get_db()
        rapport = db.execute('SELECT * FROM rapport WHERE id = %s', (id,)).fetchone()
    if not rapport:
        flash('Rapport introuvable.', FLASH_ERROR)
        return redirect(url_for('sentiers.index'))
    if rapport['user_id'] != current_user.id and not current_user.is_admin:
        flash('Non autorisé.', FLASH_ERROR)
        return redirect(url_for('sentiers.detail', id=rapport['sentier_id']))

    sentier_id = rapport['sentier_id']
    if supabase:
        supabase.table('rapport').delete().eq('id', id).execute()
    else:
        db.execute('DELETE FROM rapport WHERE id = %s', (id,))
        db.commit()
    flash('Rapport supprimé.', FLASH_SUCCESS)
    return redirect(url_for('sentiers.detail', id=sentier_id))
