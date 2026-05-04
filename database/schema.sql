-- T.R.A.I.L — Terrain Rando Alerte Info Live
-- Schéma de base de données — SQLite 3 / PostgreSQL Compatible

CREATE TABLE IF NOT EXISTS "user" (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    nom              VARCHAR(100)  NOT NULL,
    email            VARCHAR(150)  UNIQUE NOT NULL,
    mdp_hash         VARCHAR(255)  NOT NULL,
    niveau           TEXT          CHECK(niveau IN ('débutant', 'intermédiaire', 'expert')) DEFAULT 'débutant',
    localisation     VARCHAR(100),
    is_admin         BOOLEAN       DEFAULT 0,
    date_inscription DATETIME      DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sentier (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nom                 VARCHAR(150) NOT NULL,
    region              VARCHAR(100) NOT NULL,
    distance_km         REAL         NOT NULL CHECK(distance_km > 0),
    denivele_pos        INTEGER      NOT NULL CHECK(denivele_pos >= 0),
    difficulte          TEXT         NOT NULL CHECK(difficulte IN ('facile', 'moyen', 'difficile', 'expert')),
    -- Types de pratique séparés par virgule : trail, vtt, rando, ski_rando
    types_pratique      TEXT         NOT NULL DEFAULT 'trail',
    terrain             VARCHAR(100),
    saison_recommandee  VARCHAR(100),
    description         TEXT,
    user_id             INTEGER      NOT NULL,
    date_ajout          DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE
);

-- Rapport de conditions : entité métier principale
-- Remplace l'ancienne table "sortie" — centré sur la praticabilité du sentier
CREATE TABLE IF NOT EXISTS rapport (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    sentier_id       INTEGER NOT NULL,
    date_rapport     DATETIME DEFAULT CURRENT_TIMESTAMP,
    -- Expiration automatique 7 jours après le dépôt
    date_expiration  DATETIME NOT NULL,
    -- État actuel du sentier
    statut           TEXT NOT NULL CHECK(statut IN ('praticable', 'partiel', 'ferme')),
    -- Type de pratique concerné par ce rapport
    type_pratique    TEXT NOT NULL CHECK(type_pratique IN ('trail', 'vtt', 'rando', 'ski_rando')),
    -- Obstacles identifiés (valeurs séparées par virgule)
    -- ex: neige,boue | verglas | arbre_tombe,crue | travaux
    obstacles        TEXT,
    commentaire      TEXT,
    FOREIGN KEY (user_id)    REFERENCES "user"(id)     ON DELETE CASCADE,
    FOREIGN KEY (sentier_id) REFERENCES sentier(id)  ON DELETE CASCADE
);

-- Index pour optimiser les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_sentier_region       ON sentier(region);
CREATE INDEX IF NOT EXISTS idx_sentier_difficulte   ON sentier(difficulte);
CREATE INDEX IF NOT EXISTS idx_rapport_sentier      ON rapport(sentier_id);
CREATE INDEX IF NOT EXISTS idx_rapport_user         ON rapport(user_id);
CREATE INDEX IF NOT EXISTS idx_rapport_statut       ON rapport(statut);
-- Index sur expiration pour filtrer rapidement les rapports valides
CREATE INDEX IF NOT EXISTS idx_rapport_expiration   ON rapport(date_expiration);

-- Utilisateur de démonstration (demo@trail.fr / demo1234)
-- Le hash correspond à 'demo1234' via bcrypt
INSERT INTO "user" (nom, email, mdp_hash, niveau, localisation, is_admin)
SELECT 'Demo User', 'demo@trail.fr', '$2b$12$8K7M2B.R3mFh1H8vR/HqveO7H9v8v8v8v8v8v8v8v8v8v8v8v8v8v', 'expert', 'Chamonix', 1
WHERE NOT EXISTS (SELECT 1 FROM "user" WHERE email = 'demo@trail.fr');
