-- schema.sql für Ortslexikon
-- Voraussetzung: PostGIS ist bereits aktiviert
SHOW data_directory;
SELECT version();
SELECT postgis_full_version();

-- ===================================================================
--   TABELLE: ORTE (zentral)
-- ===================================================================

-- als standardt setzen
SET search_path TO landeskunde, public;

DROP TABLE IF EXISTS landeskunde.places CASCADE;

CREATE TABLE landeskunde.places (
    id SERIAL PRIMARY KEY,

    -- externe / technische ID aus Parser
    place_id INT UNIQUE,

    -- Grunddaten
    name TEXT NOT NULL,
    type TEXT,
    settlement_type TEXT,

    -- Hierarchie (optional, später befüllbar)
    parent_id INT REFERENCES landeskunde.places(id),

    -- Ersterwähnung
    first_mention_year INT,
    first_mention_source TEXT,

    -- HOL-Volltext & Lage
    description TEXT,
    lage_hinweis TEXT,

    -- Meta
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ===================================================================
--   ALTERNATIVE NAMEN (normalisiert)
-- ===================================================================

DROP TABLE IF EXISTS landeskunde.place_aliases CASCADE;

CREATE TABLE landeskunde.place_aliases (
    id SERIAL PRIMARY KEY,

    place_id INT NOT NULL
        REFERENCES landeskunde.places(id)
        ON DELETE CASCADE,

    alias TEXT NOT NULL,

    year_from INT,
    year_to INT,

    source TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);


-- ===================================================================
--   VERWALTUNGSGESCHICHTE
-- ===================================================================

CREATE TABLE landeskunde.place_admin_history (
    id SERIAL PRIMARY KEY,
    place_id INT REFERENCES landeskunde.places(id),
    year_from INT,
    year_to INT,
    admin_unit TEXT,
    admin_level TEXT,
    notes TEXT
);
-- ===================================================================
-- Gerichtszugehörigkeit
-- ===================================================================

CREATE TABLE landeskunde.place_court_history (
    id SERIAL PRIMARY KEY,
    place_id INT REFERENCES landeskunde.places(id),
    year_from INT,
    year_to INT,
    court_name TEXT,
    court_type TEXT,
    notes TEXT
);

-- ===================================================================
-- Fläche / Gemarkung
-- ===================================================================

DROP TABLE IF EXISTS landeskunde.place_area CASCADE;

CREATE TABLE landeskunde.place_area (
    id SERIAL PRIMARY KEY,

    place_id INT NOT NULL
        REFERENCES landeskunde.places(id)
        ON DELETE CASCADE,

    year INT NOT NULL,

    area_total NUMERIC NOT NULL,
    unit TEXT NOT NULL,

    categories JSONB,          -- dynamische Unterflächen
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);


-- ===================================================================
-- lord (Person / Institution)
-- ===================================================================

CREATE TABLE landeskunde.lord (
    id SERIAL PRIMARY KEY,
    name TEXT,
    type TEXT
);

-- ===================================================================
-- (Herrschaft / Lehen)
-- ===================================================================

CREATE TABLE landeskunde.place_lordship (
    id SERIAL PRIMARY KEY,
    place_id INT REFERENCES landeskunde.places(id),
    owner TEXT,
    year_from INT,
    year_to INT,
    notes TEXT,
    lord_id INT REFERENCES landeskunde.lord(id),
    share_type TEXT
);

-- ===================================================================
-- (Wirtschaft / Ökonomie)
-- ===================================================================

CREATE TABLE landeskunde.place_economy (
    id SERIAL PRIMARY KEY,
    place_id INT REFERENCES landeskunde.places(id),
    data JSONB,
    notes TEXT
);

-- ===================================================================
-- (Kirche / Patronat)
-- ===================================================================

CREATE TABLE landeskunde.place_church_history (
    id SERIAL PRIMARY KEY,

    place_id INT NOT NULL
        REFERENCES landeskunde.places(id)
        ON DELETE CASCADE,

    data JSONB NOT NULL,
    source TEXT,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);


-- ===================================================================
-- (Baudenkmale)
-- ===================================================================

CREATE TABLE landeskunde.place_monuments (
    id SERIAL PRIMARY KEY,
    place_id INT REFERENCES landeskunde.places(id),
    title TEXT,
    description TEXT,
    notes TEXT
);

-- ===================================================================
-- Bevölkerung
-- ===================================================================

CREATE TABLE landeskunde.place_population (
    id SERIAL PRIMARY KEY,

    place_id INT NOT NULL
        REFERENCES landeskunde.places(id)
        ON DELETE CASCADE,

    year INT NOT NULL,
    inhabitants INT NOT NULL,
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);


-- ===================================================================
-- Verwaltung
-- ===================================================================

DROP TABLE IF EXISTS landeskunde.place_admin CASCADE;

CREATE TABLE landeskunde.place_admin (
    id SERIAL PRIMARY KEY,

    place_id INT NOT NULL
        REFERENCES landeskunde.places(id)
        ON DELETE CASCADE,

    year_from INT,
    year_to INT,

    admin_unit TEXT NOT NULL,
    admin_level TEXT,

    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);
-- ===================================================================