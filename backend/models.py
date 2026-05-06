from flask_login import UserMixin


class User(UserMixin):
    """Représente un utilisateur de la plateforme T.R.A.I.L.
    
    Attributes:
        id (int): ID unique
        nom (str): Nom complet de l'utilisateur
        email (str): Email unique
        niveau (str): Niveau d'expérience ('débutant', 'intermédiaire', 'expert')
        localisation (str): Région/ville pour contexte géographique
        is_admin (bool): Droits administrateur (modération, suppression)
        date_inscription (str): Date d'inscription au format ISO
    """
    def __init__(self, row):
        self.id = row['id']
        self.nom = row['nom']
        self.email = row['email']
        self.mdp_hash = row['mdp_hash']
        self.niveau = row['niveau']
        self.localisation = row['localisation']
        self.is_admin = bool(row['is_admin'])
        self.date_inscription = row['date_inscription']

    def get_id(self):
        """Retourne l'ID utilisateur pour Flask-Login."""
        return str(self.id)
