# T.R.A.I.L — Terrain Rando Alerte Info Live

Plateforme communautaire simple et légère pour publier et consulter l'état des sentiers (rapports valides 7 jours).

Développé dans le cadre du cours TI616 — Numérique Durable (EFREI Paris, promotion 2025-2026).

Déploiement public : https://nume-durable.vercel.app

---

## Résumé

- **But** : Permettre aux coureurs, VTTistes et randonneurs de consulter et signaler la praticabilité des sentiers.
- **Principales fonctionnalités** : inscription / connexion, dépôt de rapports (statut, type, obstacles), consultation liste et détail des sentiers, profil utilisateur.

---

## Démo & déploiement

- URL du déploiement public : 
- Plateforme utilisée : Vercel / Supabase 

---

## 🛠 Stack technique

- Backend : Python 3.10+, Flask 3.1
- Auth : `flask-login`
- Forms / CSRF : `flask-wtf`
- Hashing : `bcrypt`
- DB production : Supabase (PostgreSQL)
- DB fallback : psycopg2 wrapper (PostgreSQL); ancien support SQLite retiré
- Rate limiting (optionnel) : `flask-limiter`
- Deployment: Vercel (config `vercel.json`) or Render (config `render.yaml`)

Fichier dépendances : `requirements.txt` / `pyproject.toml`

---

## Équipe

- Anglard Loïc
- Batard-Plaza Esteban
- Cao Lilian
- Chollet Maelle
- Danthine Mathieu

---

## Installation rapide (développement)

Prérequis : Python 3.10+, pip

Windows (PowerShell) :

```powershell
git clone <repo-url>
cd NumeDurable
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# éditer .env : définir SECRET_KEY, SUPABASE_URL/KEY ou DATABASE_URL
flask --app app init-db
flask --app app run
```

Linux / macOS :

```bash
git clone <repo-url>
cd NumeDurable
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# éditer .env : définir SECRET_KEY, SUPABASE_URL/KEY ou DATABASE_URL
flask --app app init-db
flask --app app run
```

L'application sera disponible par défaut sur `http://127.0.0.1:5000`.

---

## Structure du dépôt

Arborescence principale :

```
NumeDurable/
├─ app.py                # Entrée (factory)
├─ config.py             # Configuration (SECRET_KEY, BDD)
├─ requirements.txt
├─ pyproject.toml
├─ backend/              # Logique serveur
│  ├─ __init__.py        # create_app
│  ├─ db.py              # wrapper DB, init_db
│  ├─ models.py
│  ├─ supabase_utils.py
│  ├─ validators.py
│  └─ routes/            # blueprints (auth, users, sentiers, rapports)
├─ frontend/             # templates & static
└─ database/             # schema_postgresql.sql (schéma prod)
```

---

## Fonctionnalités principales (rapide)

- Dépôt de rapport : `rapports/nouveau` — statut, type, obstacles, commentaire
- Liste sentiers : filtre par région/difficulté, dernier rapport affiché
- Détail sentier : liste des rapports récents (+ auteurs)
- Profil utilisateur : voir ses rapports et sentiers, modifier profil

---

## Données de démonstration


- Initialiser le schéma PostgreSQL localement (si `DATABASE_URL` défini) :

```bash
flask --app app init-db
```

Le script d'initialisation peut semer des données de démonstration (voir `backend/db.py`).

---

## Contact

Pour questions / accès invitation : ouvrir une issue sur le dépôt GitHub.

---

_README généré / mis à jour par l'équipe de maintenance — compléter l'URL de déploiement publique._
db:    modification du schéma ou des requêtes BDD

docs:  documentation uniquement

test:  ajout ou modification de tests
