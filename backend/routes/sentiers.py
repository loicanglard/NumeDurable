from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from backend.db import get_db

sentiers_bp = Blueprint('sentiers', __name__, url_prefix='/sentiers')

DIFFICULTES = ['facile', 'moyen', 'difficile', 'expert']
TYPES_PRATIQUE = ['trail', 'vtt', 'rando', 'ski_rando']


@sentiers_bp.route('/')
def index():
    db = get_db()
    region = request.args.get('region', '').strip()
    difficulte = request.args.get('difficulte', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    par_page = 10

    where, params = [], []
    if region:
        where.append('region LIKE ?')
        params.append(f'%{region}%')
    if difficulte and difficulte in DIFFICULTES:
        where.append('difficulte = ?')
        params.append(difficulte)

    clause = ('WHERE ' + ' AND '.join(where)) if where else ''
    total = db.execute(f'SELECT COUNT(*) FROM sentier {clause}', params).fetchone()[0]
    sentiers = db.execute(
        f'SELECT * FROM sentier {clause} ORDER BY date_ajout DESC LIMIT ? OFFSET ?',
        params + [par_page, (page - 1) * par_page]
    ).fetchall()

    # Dernier rapport valide par sentier
    dernier_rapport = {}
    for s in sentiers:
        r = db.execute('''
            SELECT statut FROM rapport
            WHERE sentier_id = ? AND date_expiration > datetime('now')
            ORDER BY date_rapport DESC LIMIT 1
        ''', (s['id'],)).fetchone()
        dernier_rapport[s['id']] = r['statut'] if r else None

    regions = [r[0] for r in db.execute('SELECT DISTINCT region FROM sentier ORDER BY region').fetchall()]

    return render_template('sentiers/index.html',
                           sentiers=sentiers, dernier_rapport=dernier_rapport,
                           regions=regions, difficultes=DIFFICULTES,
                           region=region, difficulte=difficulte,
                           page=page, total=total, par_page=par_page)


@sentiers_bp.route('/<int:id>')
def detail(id):
    db = get_db()
    sentier = db.execute('SELECT s.*, u.nom as auteur_nom FROM sentier s JOIN users u ON s.user_id = u.id WHERE s.id = ?', (id,)).fetchone()
    if not sentier:
        flash('Sentier introuvable.', 'erreur')
        return redirect(url_for('sentiers.index'))

    rapports = db.execute('''
        SELECT r.*, u.nom as user_nom FROM rapport r
        JOIN user u ON r.user_id = u.id
        WHERE r.sentier_id = ?
        ORDER BY r.date_rapport DESC LIMIT 20
    ''', (id,)).fetchall()

    return render_template('sentiers/detail.html', sentier=sentier, rapports=rapports)


@sentiers_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau():
    import sys
    from flask import session
    print(f"DEBUG NOUVEAU: auth={current_user.is_authenticated}, id={getattr(current_user, 'id', 'N/A')}, session={list(session.keys())}", file=sys.stderr)
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
            if distance_km <= 0: raise ValueError
        except (ValueError, TypeError):
            erreurs.append('Distance invalide.')
        try:
            denivele_pos = int(denivele_pos)
            if denivele_pos < 0: raise ValueError
        except (ValueError, TypeError):
            erreurs.append('Dénivelé invalide.')
        if difficulte not in DIFFICULTES:
            erreurs.append('Difficulté invalide.')

        if erreurs:
            for e in erreurs: flash(e, 'erreur')
            return render_template('sentiers/form.html', difficultes=DIFFICULTES, types_pratique=TYPES_PRATIQUE, mode='nouveau')

        db = get_db()
        cur = db.execute(
            'INSERT INTO sentier (nom, region, distance_km, denivele_pos, difficulte, types_pratique, terrain, saison_recommandee, description, user_id) VALUES (?,?,?,?,?,?,?,?,?,?)',
            (nom, region, distance_km, denivele_pos, difficulte, types_pratique, terrain or None, saison_recommandee or None, description or None, current_user.id)
        )
        db.commit()
        flash('Sentier ajouté avec succès !', 'succes')
        return redirect(url_for('sentiers.detail', id=cur.lastrowid))

    return render_template('sentiers/form.html', difficultes=DIFFICULTES, types_pratique=TYPES_PRATIQUE, mode='nouveau')


@sentiers_bp.route('/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier(id):
    db = get_db()
    sentier = db.execute('SELECT * FROM sentier WHERE id = ?', (id,)).fetchone()
    if not sentier:
        flash('Sentier introuvable.', 'erreur')
        return redirect(url_for('sentiers.index'))
    if sentier['user_id'] != current_user.id and not current_user.is_admin:
        flash('Non autorisé.', 'erreur')
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
            for e in erreurs: flash(e, 'erreur')
            return render_template('sentiers/form.html', sentier=sentier, difficultes=DIFFICULTES, types_pratique=TYPES_PRATIQUE, mode='modifier')

        db.execute(
            'UPDATE sentier SET nom=?, region=?, distance_km=?, denivele_pos=?, difficulte=?, types_pratique=?, terrain=?, saison_recommandee=?, description=? WHERE id=?',
            (nom, region, distance_km, denivele_pos, difficulte, types_pratique, terrain or None, saison_recommandee or None, description or None, id)
        )
        db.commit()
        flash('Sentier modifié.', 'succes')
        return redirect(url_for('sentiers.detail', id=id))

    return render_template('sentiers/form.html', sentier=sentier, difficultes=DIFFICULTES, types_pratique=TYPES_PRATIQUE, mode='modifier')


@sentiers_bp.route('/<int:id>/supprimer', methods=['POST'])
@login_required
def supprimer(id):
    db = get_db()
    sentier = db.execute('SELECT * FROM sentier WHERE id = ?', (id,)).fetchone()
    if not sentier:
        flash('Sentier introuvable.', 'erreur')
        return redirect(url_for('sentiers.index'))
    if sentier['user_id'] != current_user.id and not current_user.is_admin:
        flash('Non autorisé.', 'erreur')
        return redirect(url_for('sentiers.detail', id=id))

    db.execute('DELETE FROM sentier WHERE id = ?', (id,))
    db.commit()
    flash('Sentier supprimé.', 'succes')
    return redirect(url_for('sentiers.index'))
