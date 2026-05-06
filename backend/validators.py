"""Validateurs pour les formulaires utilisateur.

Ce module centralise la logique de validation pour éviter la duplication
et rendre le code des routes plus lisible.
"""

from backend.constants import DIFFICULTES, TYPES_PRATIQUE, NIVEAUX, STATUTS


def validate_sentier_form(data):
    """Valide les données d'un formulaire de sentier.
    
    Args:
        data: dict avec les clés suivantes:
            - nom (str)
            - region (str)
            - distance_km (str ou float)
            - denivele_pos (str ou int)
            - difficulte (str)
            - description (str, optionnel)
    
    Returns:
        tuple: (is_valid: bool, erreurs: list of str)
    """
    erreurs = []
    
    # Validation du nom
    if not data.get('nom', '').strip():
        erreurs.append('Le nom est requis.')
    
    # Validation de la région
    if not data.get('region', '').strip():
        erreurs.append('La région est requise.')
    
    # Validation de la distance
    try:
        distance_km = float(data.get('distance_km', 0))
        if distance_km <= 0:
            raise ValueError
    except (ValueError, TypeError):
        erreurs.append('Distance invalide.')
    
    # Validation du dénivelé
    try:
        denivele_pos = int(data.get('denivele_pos', 0))
        if denivele_pos < 0:
            raise ValueError
    except (ValueError, TypeError):
        erreurs.append('Dénivelé invalide.')
    
    # Validation de la difficulté
    if data.get('difficulte') not in DIFFICULTES:
        erreurs.append('Difficulté invalide.')
    
    # Validation de la description
    description = data.get('description', '').strip()
    if len(description) > 2000:
        erreurs.append('La description ne peut pas dépasser 2000 caractères.')
    
    return len(erreurs) == 0, erreurs


def validate_user_signup(data):
    """Valide les données d'inscription utilisateur.
    
    Args:
        data: dict avec les clés:
            - nom (str)
            - email (str)
            - mdp (str)
            - mdp_confirm (str)
            - niveau (str)
    
    Returns:
        tuple: (is_valid: bool, erreurs: list of str)
    """
    erreurs = []
    
    nom = data.get('nom', '').strip()
    if not nom:
        erreurs.append('Le nom est requis.')
    
    email = data.get('email', '').strip().lower()
    if not email or '@' not in email:
        erreurs.append('Email invalide.')
    
    mdp = data.get('mdp', '')
    if len(mdp) < 8:
        erreurs.append('Le mot de passe doit faire au moins 8 caractères.')
    
    mdp_confirm = data.get('mdp_confirm', '')
    if mdp != mdp_confirm:
        erreurs.append('Les mots de passe ne correspondent pas.')
    
    niveau = data.get('niveau', 'débutant')
    if niveau not in NIVEAUX:
        erreurs.append('Niveau invalide.')
    
    return len(erreurs) == 0, erreurs


def validate_user_profile_update(data):
    """Valide la mise à jour de profil utilisateur.
    
    Args:
        data: dict avec les clés:
            - nom (str)
            - niveau (str)
            - mdp (str, optionnel)
            - mdp_confirm (str, optionnel)
    
    Returns:
        tuple: (is_valid: bool, erreurs: list of str)
    """
    erreurs = []
    
    nom = data.get('nom', '').strip()
    if not nom:
        erreurs.append('Le nom est requis.')
    
    niveau = data.get('niveau', '')
    if niveau not in NIVEAUX:
        erreurs.append('Niveau invalide.')
    
    # Validation optionnelle du mot de passe (si fourni)
    mdp = data.get('mdp', '')
    if mdp:
        if len(mdp) < 8:
            erreurs.append('Mot de passe trop court (8 car. min).')
        
        mdp_confirm = data.get('mdp_confirm', '')
        if mdp != mdp_confirm:
            erreurs.append('Les mots de passe ne correspondent pas.')
    
    return len(erreurs) == 0, erreurs


def validate_rapport_form(data):
    """Valide les données d'un rapport de conditions.
    
    Args:
        data: dict avec les clés:
            - sentier_id (int)
            - statut (str)
            - type_pratique (str)
    
    Returns:
        tuple: (is_valid: bool, erreurs: list of str)
    """
    erreurs = []
    
    sentier_id = data.get('sentier_id')
    if not sentier_id:
        erreurs.append('Sentier requis.')
    
    statut = data.get('statut', '')
    if statut not in STATUTS:
        erreurs.append('Statut invalide.')
    
    type_pratique = data.get('type_pratique', '')
    if type_pratique not in TYPES_PRATIQUE:
        erreurs.append('Type de pratique invalide.')
    
    return len(erreurs) == 0, erreurs
