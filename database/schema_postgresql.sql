-- T.R.A.I.L — Terrain Rando Alerte Info Live
-- Schéma PostgreSQL pour Supabase
-- Créé automatiquement lors de l'initialisation

CREATE TABLE IF NOT EXISTS "user" (
    id               SERIAL PRIMARY KEY,
    nom              VARCHAR(100)  NOT NULL,
    email            VARCHAR(150)  UNIQUE NOT NULL,
    mdp_hash         TEXT           NOT NULL,
    niveau           VARCHAR(20)   CHECK(niveau IN ('débutant', 'intermédiaire', 'expert')) DEFAULT 'débutant',
    localisation     VARCHAR(100),
    is_admin         BOOLEAN       DEFAULT FALSE,
    date_inscription TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    created_at       TIMESTAMP,
    updated_at       TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sentier (
    id                  SERIAL PRIMARY KEY,
    nom                 VARCHAR(150) NOT NULL,
    region              VARCHAR(100) NOT NULL,
    distance_km         REAL         NOT NULL CHECK(distance_km > 0),
    denivele_pos        INTEGER      NOT NULL CHECK(denivele_pos >= 0),
    difficulte          VARCHAR(20)  NOT NULL CHECK(difficulte IN ('facile', 'moyen', 'difficile', 'expert')),
    -- Types de pratique séparés par virgule : trail, vtt, rando, ski_rando
    types_pratique      TEXT         NOT NULL DEFAULT 'trail',
    terrain             VARCHAR(100),
    saison_recommandee  VARCHAR(100),
    description         TEXT,
    user_id             INTEGER      NOT NULL,
    date_ajout          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE
);

-- Rapport de conditions : entité métier principale
-- Remplace l'ancienne table "sortie" — centré sur la praticabilité du sentier
CREATE TABLE IF NOT EXISTS rapport (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER NOT NULL,
    sentier_id       INTEGER NOT NULL,
    date_rapport     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Expiration automatique 7 jours après le dépôt
    date_expiration  TIMESTAMP NOT NULL,
    -- État actuel du sentier
    statut           VARCHAR(20) NOT NULL CHECK(statut IN ('praticable', 'partiel', 'ferme')),
    -- Type de pratique concerné par ce rapport
    type_pratique    VARCHAR(20) NOT NULL CHECK(type_pratique IN ('trail', 'vtt', 'rando', 'ski_rando')),
    -- Obstacles identifiés (valeurs séparées par virgule)
    -- ex: neige,boue | verglas | arbre_tombe,crue | travaux
    obstacles        TEXT,
    commentaire      TEXT,
    created_at       TIMESTAMP,
    updated_at       TIMESTAMP,
    FOREIGN KEY (user_id)    REFERENCES "user"(id)     ON DELETE CASCADE,
    FOREIGN KEY (sentier_id) REFERENCES sentier(id)  ON DELETE CASCADE
);

-- Index pour optimiser les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_sentier_region       ON sentier(region);
CREATE INDEX IF NOT EXISTS idx_sentier_difficulte   ON sentier(difficulte);
CREATE INDEX IF NOT EXISTS idx_rapport_sentier      ON rapport(sentier_id);
CREATE INDEX IF NOT EXISTS idx_rapport_user         ON rapport(user_id);
CREATE INDEX IF NOT EXISTS idx_rapport_expiration   ON rapport(date_expiration);
