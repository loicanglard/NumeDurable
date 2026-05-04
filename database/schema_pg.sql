-- T.R.A.I.L — schéma PostgreSQL (Supabase)
-- Utilisé uniquement quand DATABASE_URL est défini (déploiement Vercel)

CREATE TABLE IF NOT EXISTS "user" (
    id               SERIAL PRIMARY KEY,
    nom              VARCHAR(100)  NOT NULL,
    email            VARCHAR(150)  UNIQUE NOT NULL,
    mdp_hash         VARCHAR(255)  NOT NULL,
    niveau           TEXT          CHECK(niveau IN ('débutant', 'intermédiaire', 'expert')) DEFAULT 'débutant',
    localisation     VARCHAR(100),
    is_admin         BOOLEAN       DEFAULT FALSE,
    date_inscription TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sentier (
    id                  SERIAL PRIMARY KEY,
    nom                 VARCHAR(150) NOT NULL,
    region              VARCHAR(100) NOT NULL,
    distance_km         REAL         NOT NULL CHECK(distance_km > 0),
    denivele_pos        INTEGER      NOT NULL CHECK(denivele_pos >= 0),
    difficulte          TEXT         NOT NULL CHECK(difficulte IN ('facile', 'moyen', 'difficile', 'expert')),
    types_pratique      TEXT         NOT NULL DEFAULT 'trail',
    terrain             VARCHAR(100),
    saison_recommandee  VARCHAR(100),
    description         TEXT,
    user_id             INTEGER      NOT NULL,
    date_ajout          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rapport (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER  NOT NULL,
    sentier_id       INTEGER  NOT NULL,
    date_rapport     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_expiration  TIMESTAMP NOT NULL,
    statut           TEXT NOT NULL CHECK(statut IN ('praticable', 'partiel', 'ferme')),
    type_pratique    TEXT NOT NULL CHECK(type_pratique IN ('trail', 'vtt', 'rando', 'ski_rando')),
    obstacles        TEXT,
    commentaire      TEXT,
    FOREIGN KEY (user_id)    REFERENCES "user"(id)    ON DELETE CASCADE,
    FOREIGN KEY (sentier_id) REFERENCES sentier(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sentier_region      ON sentier(region);
CREATE INDEX IF NOT EXISTS idx_sentier_difficulte  ON sentier(difficulte);
CREATE INDEX IF NOT EXISTS idx_rapport_sentier     ON rapport(sentier_id);
CREATE INDEX IF NOT EXISTS idx_rapport_user        ON rapport(user_id);
CREATE INDEX IF NOT EXISTS idx_rapport_statut      ON rapport(statut);
CREATE INDEX IF NOT EXISTS idx_rapport_expiration  ON rapport(date_expiration);