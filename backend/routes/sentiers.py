from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime

from backend.constants import DIFFICULTES, TYPES_PRATIQUE, FLASH_ERROR, FLASH_SUCCESS
from backend.validators import validate_sentier_form
sentiers_bp = Blueprint('sentiers', __name__, url_prefix='/sentiers')


@sentiers_bp.route('/')
def index():
    supabase = current_app.supabase
    region = request.args.get('region', '').strip()
    difficulte = request.args.get('difficulte', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    par_page = 10

    where, params = [], []
    if region:
        where.append('region ILIKE %s')
        params.append(f'%{region}%')
    if difficulte and difficulte in DIFFICULTES:
        where.append('difficulte = %s')
        params.append(difficulte)

    # Build supabase query with filters
    query = supabase.table('sentier').select('*')
    if region:
        query = query.filter('region', 'ilike', f'%{region}%')
    if difficulte and difficulte in DIFFICULTES:
        query = query.eq('difficulte', difficulte)
    # Total count
    total_resp = query.select('id', count='exact').execute()
    total = total_resp.count or 0
    # Pagination
    sentiers_resp = query.order('date_ajout', desc=True).limit(par_page).offset((page - 1) * par_page).execute()
    sentiers = sentiers_resp.data or []

    # TODO: Optimiser avec pagination côté DB (LIMIT 0, 10) dès que effectif > 500 sentiers
    # Actuellement performant, mais devient lent avec beaucoup de données
    
    # Dernier rapport valide pour tous les sentiers affichés en une seule requête.
    # Stratégie : récupérer le rapport le plus récent (max date_rapport) non expiré
    # pour chaque sentier, en une requête optimisée. On utilise une sous-requête
    # pour récupérer les MAX dates, puis on join pour éviter les GROUP BY dupliqués.
    dernier_rapport = {}
    # Fetch latest valid report status per displayed sentier (client-side aggregation)
    dernier_rapport = {}
    if sentiers:
        sentier_ids = [s['id'] for s in sentiers]
        rapports_resp = supabase.table('rapport').select('*').in_('sentier_id', sentier_ids).gt('date_expiration', datetime.utcnow().isoformat()).order('date_rapport', desc=True).execute()
        rows = rapports_resp.data or []
        seen = set()
        for r in rows:
            sid = r.get('sentier_id')
            if sid not in seen:
                dernier_rapport[sid] = r.get('statut')
                seen.add(sid)

    regions_resp = supabase.table('sentier').select('region').execute()
    regions = sorted({r.get('region') for r in (regions_resp.data or []) if r.get('region')})

    return render_template('sentiers/index.html',
                           sentiers=sentiers, dernier_rapport=dernier_rapport,
                           regions=regions, difficultes=DIFFICULTES,
                           region=region, difficulte=difficulte,
                           page=page, total=total, par_page=par_page)


@sentiers_bp.route('/<int:id>')
def detail(id):
    supabase = current_app.supabase
    # Fetch sentier and its author
    sentier_resp = supabase.table('sentier').select('*, "user":user(nom)').eq('id', id).execute()
    sentiers = sentier_resp.data or []
    sentier = sentiers[0] if sentiers else None
    if not sentier:
        flash('Sentier introuvable.', FLASH_ERROR)
        return redirect(url_for('sentiers.index'))

    # Fetch rapports and attach user_nom
    rapports_resp = supabase.table('rapport').select('*').eq('sentier_id', id).order('date_rapport', desc=True).limit(20).execute()
    rapports = rapports_resp.data or []
    # Attach user names for rapports (batch fetch unique users)
    user_ids = sorted({r.get('user_id') for r in rapports if r.get('user_id')})
    if user_ids:
        users_resp = supabase.table('user').select('id, nom').in_('id', user_ids).execute()
        users_map = {u['id']: u['nom'] for u in (users_resp.data or [])}
        for r in rapports:
            r['user_nom'] = users_map.get(r.get('user_id'))

    return render_template('sentiers/detail.html', sentier=sentier, rapports=rapports)


@sentiers_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau():
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        region = request.form.get('region', '').strip()
        distance_km = request.form.get('distance_km', '')
        denivele_pos = request.form.get('denivele_pos', '')
        difficulte = request.form.get('difficulte', '')
        types_pratique = ','.join(request.form.getlist('types_pratique')) or 'trail'
        terrain = request.form.get('terrain', '').strip()
        saison_recommandee = request.form.get('saison_recommandee', '').strip()
        description = request.form.get('description', '').strip()

        # Valider via le helper centralisé
        form_data = {
            'nom': nom,
            'region': region,
            'distance_km': distance_km,
            'denivele_pos': denivele_pos,
            'difficulte': difficulte,
            'description': description
        }
        is_valid, erreurs = validate_sentier_form(form_data)
        
        if not is_valid:
            for e in erreurs: flash(e, FLASH_ERROR)
            return render_template('sentiers/form.html', difficultes=DIFFICULTES, types_pratique=TYPES_PRATIQUE, mode='nouveau')

        supabase = current_app.supabase
        now = datetime.utcnow()
        distance_km_float = float(distance_km)
        denivele_pos_int = int(denivele_pos)
        insert_payload = {
            'nom': nom,
            'region': region,
            'distance_km': distance_km_float,
            'denivele_pos': denivele_pos_int,
            'difficulte': difficulte,
            'types_pratique': types_pratique,
            'terrain': terrain or None,
            'saison_recommandee': saison_recommandee or None,
            'description': description or None,
            'user_id': current_user.id,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat()
        }
        resp = supabase.table('sentier').insert(insert_payload).select('id').execute()
        new_id = resp.data[0]['id'] if (resp.data and len(resp.data) > 0) else None
        flash('Sentier ajouté avec succès !', FLASH_SUCCESS)
        return redirect(url_for('sentiers.detail', id=new_id))

    return render_template('sentiers/form.html', difficultes=DIFFICULTES, types_pratique=TYPES_PRATIQUE, mode='nouveau')


@sentiers_bp.route('/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier(id):
    supabase = current_app.supabase
    sentier_resp = supabase.table('sentier').select('*').eq('id', id).execute()
    sentier = sentier_resp.data[0] if (sentier_resp.data and len(sentier_resp.data) > 0) else None
    if not sentier:
        flash('Sentier introuvable.', FLASH_ERROR)
        return redirect(url_for('sentiers.index'))
    if sentier['user_id'] != current_user.id and not current_user.is_admin:
        flash('Non autorisé.', FLASH_ERROR)
        return redirect(url_for('sentiers.detail', id=id))

    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        region = request.form.get('region', '').strip()
        distance_km = request.form.get('distance_km', '')
        denivele_pos = request.form.get('denivele_pos', '')
        difficulte = request.form.get('difficulte', '')
        types_pratique = ','.join(request.form.getlist('types_pratique')) or 'trail'
        terrain = request.form.get('terrain', '').strip()
        saison_recommandee = request.form.get('saison_recommandee', '').strip()
        description = request.form.get('description', '').strip()

        erreurs = []
        if not nom: erreurs.append('Le nom est requis.')
        if not region: erreurs.append('La région est requise.')
        try:
            distance_km = float(distance_km)
        except (ValueError, TypeError):
            erreurs.append('Distance invalide.')
        try:
            denivele_pos = int(denivele_pos)
        except (ValueError, TypeError):
            erreurs.append('Dénivelé invalide.')

        if erreurs:
            for e in erreurs: flash(e, FLASH_ERROR)
            return render_template('sentiers/form.html', sentier=sentier, difficultes=DIFFICULTES, types_pratique=TYPES_PRATIQUE, mode='modifier')

        supabase.table('sentier').update({
            'nom': nom,
            'region': region,
            'distance_km': distance_km,
            'denivele_pos': denivele_pos,
            'difficulte': difficulte,
            'types_pratique': types_pratique,
            'terrain': terrain or None,
            'saison_recommandee': saison_recommandee or None,
            'description': description or None,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', id).execute()
        flash('Sentier modifié.', FLASH_SUCCESS)
        return redirect(url_for('sentiers.detail', id=id))

    return render_template('sentiers/form.html', sentier=sentier, difficultes=DIFFICULTES, types_pratique=TYPES_PRATIQUE, mode='modifier')


@sentiers_bp.route('/<int:id>/supprimer', methods=['POST'])
@login_required
def supprimer(id):
    supabase = current_app.supabase
    sentier_resp = supabase.table('sentier').select('*').eq('id', id).execute()
    sentier = sentier_resp.data[0] if (sentier_resp.data and len(sentier_resp.data) > 0) else None
    if not sentier:
        flash('Sentier introuvable.', FLASH_ERROR)
        return redirect(url_for('sentiers.index'))
    if sentier['user_id'] != current_user.id and not current_user.is_admin:
        flash('Non autorisé.', FLASH_ERROR)
        return redirect(url_for('sentiers.detail', id=id))

    supabase.table('sentier').delete().eq('id', id).execute()
    flash('Sentier supprimé.', FLASH_SUCCESS)
    return redirect(url_for('sentiers.index'))
