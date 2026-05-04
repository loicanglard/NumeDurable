from flask_login import UserMixin


class User(UserMixin):
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
        return str(self.id)
