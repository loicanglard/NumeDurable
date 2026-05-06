# T.R.A.I.L — Terrain Rando Alerte Info Live

**Ce sentier est-il praticable aujourd'hui ?**

T.R.A.I.L est une plateforme communautaire pour trail runners, VTTistes et randonneurs : consultez et partagez l'état réel des sentiers en montagne. Les rapports de conditions sont déposés par la communauté et expirent automatiquement après 7 jours, garantissant des données fraîches et fiables.

> Projet réalisé dans le cadre du cours **TI616 — Numérique Durable** (EFREI Paris, 2025-2026).

**Équipe** : Danthine Mathieu, Anglard Loïc, Cao Lilian, Chollet Maelle, Batard-Plaza Esteban

---

## 🎯 Comment ça marche

### Vue utilisateur

1. **Accueil** : Voir les 5 derniers rapports publiés (depuis moins d'une heure à plusieurs jours)
2. **Explorer sentiers** : Parcourir la liste (filtrer par région/difficulté), voir le dernier signalement pour chaque
3. **Détail sentier** : Voir tous les rapports récents (moins de 7 jours) pour ce sentier
4. **Publier un rapport** : Indiquer l'état (praticable / partiel / fermé) + obstacles rencontrés
5. **Profil** : Consulter ses contributions + modifier ses paramètres

### Flux métier

- **Rapport** = observation horodatée d'un utilisateur pour un sentier
- **Validité** = 7 jours max (puis automatiquement ignoré par les requêtes)
- **État** = praticable, partiel, ou fermé
- **Obstacles** = tags multiples (neige, boue, arbre tombé, etc.) pour signaler les problèmes spécifiques

---

## 🛠️ Stack technique

| Composant | Technologie | Justification Green IT |
|-----------|-------------|----------------------|
| **Back-end** | Python Flask 3.1 | Micro-framework minimaliste, ~4 dépendances en prod seulement |
| **Base de données** | SQLite 3 | Fichier unique, 0 serveur externe, 0 requêtes réseau |
| **Templates** | Jinja2 (Flask) | Rendu côté serveur, 0 framework JS, pas d'API REST |
| **CSS** | Natif (variables, flexbox) | < 10 Ko minifié, polices système uniquement |
| **JS** | Vanilla (< 30 lignes) | Uniquement pour confirmations, pas de dépendances |
| **Déploiement** | Render.com | Gratuit + CI/CD GitHub auto, hébergement sobre |

**Philosophie** : Chaque choix prioritize la sobriété numérique (empreinte carbone faible, pages ultra-légères).

---

## 🚀 Lancer le projet localement

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

## 🤔 Choix techniques et compromis

### Pourquoi SQLite et pas PostgreSQL / MySQL ?

**SQLite** = une seule base de données (fichier `.db`), zéro serveur externe, zéro requêtes réseau pour la BDD. Parfait pour :
- Petite à moyenne charge (quelques centaines d'utilisateurs)
- Déploiement simple (Render gratuit peut héberger des fichiers)
- Empreinte carbone minimale (pas de serveur dédié)

**Limite** : Pas optimisé pour > 10K requêtes/sec concurrentes. Acceptable pour un projet étudiant régional.

### Pourquoi pas d'ORM (SQLAlchemy) ?

Code SQL brut avec paramètres est plus simple à apprendre et plus transparent. L'ORM ajoute une couche d'abstraction peu utile ici (requêtes simples).

**Avantage** : Déboguer une requête SQL en 10 lignes vs tracer une ORM complexe = gain de temps.

### Pas d'API REST ?

La plateforme n'expose que du rendu HTML/Jinja2. Une API ajoute des endpoints supplémentaires = surface d'attaque, overhead.

**Futur** : Si besoin d'une mobile app, l'API REST sera facile à ajouter (endpoints `/api/sentiers`, etc.).

---

## ⚠️ Limitations actuelles & améliorations futures

### Limitations

- ❌ **Pas de pagination côté client** : Liste des sentiers peut être lente avec > 500 entrées
- ❌ **Géolocalisation absente** : Les sentiers sont filtrés par région (texte), pas par coordonnées GPS
- ❌ **Pas de notifications** : Utilisateur ne sait pas si son rapport a été marqué utile/obsolète
- ❌ **Rate limiting optionnel** : Activé en prod seulement (dépend de `flask_limiter`)
- ❌ **Tests partiels** : Sentiers et rapports couverts, auth/users en cours

### Améliora futures possibles

1. **Intégration Overpass API** : Récupérer les sentiers OpenStreetMap automatiquement
2. **Alerts email** : Notifier utilisateur quand un rapport = posté pour "ses" sentiers
3. **Modération communautaire** : Signaler rapports obsolètes/incorrects
4. **Statistiques** : Dashboard d'activité (rapports/semaine, utilisateurs actifs, etc.)
5. **Hors ligne** : PWA pour consulter sans réseau

---

## 🧪 Développement & tests

### Lancer les tests

```bash
pytest tests/
```

### Charger des données de démonstration

```bash
flask --app app init-db  # Déjà inclus ci-dessus
```

Les tests incluent des données de démo automatiquement.

### Accès administrateur

L'utilisateur demo créé à l'init-db a les droits admin :
- Email: `demo@trail.fr`
- Mot de passe: `demo1234`

Peut supprimer/modifier tout sentier et rapport.

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


