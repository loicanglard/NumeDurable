# T.R.A.I.L — Terrain Rando Alerte Info Live

**Ce sentier est-il praticable aujourd'hui ?**

T.R.A.I.L est une plateforme communautaire sobre permettant aux pratiquants trail, VTT et randonnée de consulter et partager l'état réel des sentiers. Les rapports de conditions (praticable / partiel / fermé) sont déposés par la communauté et expirent automatiquement après 7 jours pour garantir des données toujours fraîches.

> Projet réalisé dans le cadre du cours **TI616 — Numérique Durable** (EFREI Paris, 2025-2026).

Les membres de l'équipe sont : 
Danthine Mathieu
Anglard Loïc
Cao Lilian
Chollet Maelle
Batard-Plaza Esteban
---



## Stack technique

| Composant | Technologie | Justification Green IT |
|-----------|-------------|----------------------|
| Back-end | Python Flask 3.1 | Micro-framework, 4 dépendances en prod |
| Base de données | SQLite 3 | Fichier unique, 0 serveur réseau |
| Templates | Jinja2 (inclus Flask) | Rendu serveur, 0 JS framework |
| CSS | Natif (variables, flexbox) | < 10 Ko, polices système uniquement |
| JS | Vanilla (< 30 lignes) | Uniquement pour les confirmations |
| Déploiement | Render.com | Gratuit, CI/CD GitHub, hébergement sobre |

---

## Lancer le projet localement

### Prérequis

- Python 3.10+
- pip

### Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/alifarce/ti616_projet.git
cd ti616_projet

# 2. Créer et activer un environnement virtuel
python3 -m venv .venv
source .venv/bin/activate       # Linux / macOS
# ou : .venv\Scripts\activate   # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
cp .env.example .env
# Éditer .env et définir SECRET_KEY

# 5. Initialiser la base de données
flask --app app init-db

# 6. Lancer le serveur de développement
flask --app app run
```

Le site est accessible sur `http://127.0.0.1:5000`.

## Structure du dépôt

```
ti616_projet/
│
├── app.py                      # Point d'entrée Flask (factory)
├── config.py                   # Configuration (clé secrète, BDD)
├── requirements.txt            # Dépendances Python (prod uniquement)
├── .env.example                # Modèle de variables d'environnement
├── .gitignore
│
├── backend/                    # Logique serveur
│   ├── db.py                   # Connexion SQLite, helpers
│   └── routes/
│       ├── auth.py             # Inscription, connexion, déconnexion
│       ├── users.py            # Profil, modification, suppression compte
│       ├── sentiers.py         # CRUD sentiers
│       └── rapports.py         # CRUD rapports de conditions
│
├── frontend/                   # Interface utilisateur
│   ├── templates/              # Templates Jinja2
│   │   ├── base.html           # Layout commun (nav, footer, flash)
│   │   ├── index.html          # Page d'accueil (signalements récents)
│   │   ├── auth/               # Inscription, connexion
│   │   ├── users/              # Profil, liste admin
│   │   ├── sentiers/           # Liste, détail, formulaires
│   │   └── rapports/           # Formulaires dépôt/modification
│   └── static/
│       ├── css/style.css       # Feuille de style unique (< 10 Ko)
│       └── js/main.js          # JS minimal (confirmations)
│
├── database/
│   └── schema.sql              # Tables user, sentier, rapport + index
│
└── docs/
    ├── conception/
    │   ├── proposition_valeur.md
    │   ├── user_stories.md
    │   ├── backlog.md
    │   ├── choix_techniques.md
    │   ├── sobriete_numerique.md
    │   └── uml/
    │       ├── cas_utilisation.puml
    │       ├── classes.puml
    │       └── sequence.puml
    └── wireframes/
        ├── accueil.md
        ├── liste_sentiers.md
        ├── detail_sentier.md
        └── profil.md
```

---

## Conventions de commit

```
feat:  nouvelle fonctionnalité
fix:   correction de bug
style: modifications CSS/HTML sans impact fonctionnel
db:    modification du schéma ou des requêtes BDD
docs:  documentation uniquement
test:  ajout ou modification de tests
ci:    configuration GitHub Actions
```

## Indicateurs Green IT visés

| Indicateur | Objectif |
|------------|---------|
| Poids d'une page | < 200 Ko |
| Requêtes HTTP / page | < 10 |
| Score EcoIndex | A ou B |
| Score Lighthouse Performance | > 85 / 100 |
| CO₂ / visite (Website Carbon) | < 0,05 g |


-------


