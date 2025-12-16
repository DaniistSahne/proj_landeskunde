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

CREATE TABLE landeskunde.place_aliases (
    hol_code SERIAL PRIMARY KEY,
    place_id INT REFERENCES landeskunde.places(id),
    alias TEXT,
    alias_type TEXT,
    year_from INT,
    year_to INT,
    source TEXT
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

CREATE TABLE landeskunde.place_area (
    id SERIAL PRIMARY KEY,
    place_id INT REFERENCES landeskunde.places(id),
    year INT,
    area_total NUMERIC,
    area_farmland NUMERIC,
    area_meadows NUMERIC,
    area_forest NUMERIC,
    area_other NUMERIC,
    unit TEXT
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

CREATE TABLE landeskunde.place_religion_history (
    id SERIAL PRIMARY KEY,
    place_id INT REFERENCES landeskunde.places(id),
    data JSONB,
    last_updated TIMESTAMP DEFAULT now()
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
    place_id INT REFERENCES landeskunde.places(id),
    year INT,
    inhabitants INT,
    notes TEXT
);

-- ===================================================================
-- Bevölkerung
-- ===================================================================

