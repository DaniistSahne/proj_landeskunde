-- schema.sql für Ortslexikon
-- Voraussetzung: PostGIS ist bereits aktiviert
SHOW data_directory;
SELECT version();
SELECT postgis_full_version();


-- als standardt setzen
SET search_path TO landeskunde, public;

-- ===================================================================
--   TABELLE: ORTE (zentral)
-- ===================================================================

CREATE TABLE places (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    shortname TEXT,
    type TEXT,                                         -- Dorf, Vorwerk, Stadtteil, Wüstung
    parent_id INTEGER REFERENCES places(id) ON DELETE SET NULL,
    alt_names JSONB,                                   -- einfache alternative Namensformen
    geometry GEOMETRY(Point, 4326),                    -- lon/lat
    first_mention_year INT,
    first_mention_source TEXT,
    settlement_type TEXT,                               -- z.B. Straßendorf
    description TEXT,
    wikidata_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ===================================================================
--   ALTERNATIVE NAMEN (normalisiert)
-- ===================================================================

CREATE TABLE place_aliases (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_type TEXT,            -- historisch, Abkürzung, Variante
    year_from INT,
    year_to INT,
    notes TEXT
);

-- ===================================================================
--   BEZIEHUNGEN (Vorwerk-von, eingemeindet-nach, Wüstung-von ...)
-- ===================================================================

CREATE TABLE place_relations (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    related_place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,       -- vorwerk_von, eingemeindet_nach, teil_von, wuestung_von
    year INT,
    notes TEXT
);

-- ===================================================================
--   VERWALTUNGSGESCHICHTE
-- ===================================================================

CREATE TABLE place_admin_history (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id),
    year_from INT,
    year_to INT,
    admin_unit TEXT,                  -- Amt, Kreis, Provinz, Königreich
    admin_level TEXT,                 -- Ebene: Amt, Kreis, Land, Staat
    notes TEXT
);

-- ===================================================================
--   RELIGION & KIRCHLICHE ANGABEN
-- ===================================================================

CREATE TABLE place_religion_history (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id),
    year_from INT,
    year_to INT,
    confession TEXT,                  -- ev., kath., ref.
    church_relation TEXT,             -- Filial von, eingepfarrt nach
    patronage TEXT,                   -- Kirchenpatron
    notes TEXT
);

-- ===================================================================
--   HERRSCHAFT / GUTSBESITZER / LEHEN
-- ===================================================================

CREATE TABLE place_lordship (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    owner TEXT NOT NULL,              -- Familie, Kloster, Herr
    year_from INT,
    year_to INT,
    notes TEXT
);

-- ===================================================================
--   BEVÖLKERUNG
-- ===================================================================

CREATE TABLE place_population (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    year INT NOT NULL,
    inhabitants INT,
    households INT,
    source_id INTEGER REFERENCES sources(id),
    notes TEXT
);

-- ===================================================================
--   FLÄCHEN- / GEMARKUNGSANGABEN
-- ===================================================================

CREATE TABLE place_area (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    year INT,
    area_total NUMERIC,
    area_farmland NUMERIC,
    area_meadows NUMERIC,
    area_forest NUMERIC,
    area_other NUMERIC,
    notes TEXT
);

-- ===================================================================
--   WIRTSCHAFT (flexibel als JSONB)
-- ===================================================================

CREATE TABLE place_economy (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id),
    year INT,
    data JSONB,                      -- {"pflüge":2,"schafe":120,"mühlen":1}
    notes TEXT
);

-- ===================================================================
--   BAUDENKMALE
-- ===================================================================

CREATE TABLE place_monuments (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id),
    title TEXT NOT NULL,
    description TEXT,
    year INT,
    notes TEXT
);

-- ===================================================================
--   BILDER / MEDIEN
-- ===================================================================

CREATE TABLE place_media (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    title TEXT,
    type TEXT,                  -- Foto, Ansicht, Karte, Plan
    source TEXT,
    license TEXT,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ===================================================================
--   DIAGRAMMDATEN (JSONB)
-- ===================================================================

CREATE TABLE place_charts (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    chart_type TEXT NOT NULL,
    data JSONB NOT NULL,         -- geeignet für Chart.js, Recharts, Plotly
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ===================================================================
--   QUELLEN
-- ===================================================================

CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    citation TEXT NOT NULL,
    url TEXT,
    year INT,
    notes TEXT
);

CREATE TABLE place_sources (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    notes TEXT
);

-- ===============================
--   INDEXE FÜR PLACES
-- ===============================

-- Volltext-Index auf Name + Notizen
CREATE INDEX IF NOT EXISTS idx_places_tsv
ON places
USING GIN (to_tsvector('german', coalesce(name,'') || ' ' || coalesce(notes,'')));

-- Geo-Index: nutzt longitude + latitude als Punkt
-- Wir erzeugen einen virtuellen Geometry-Punkt für den Index
CREATE INDEX IF NOT EXISTS idx_places_geom
ON places
USING GIST (ST_SetSRID(ST_MakePoint(longitude, latitude), 4326));

-- Optional: Index auf parent_id für schnellere Abfragen von Beziehungen
CREATE INDEX IF NOT EXISTS idx_places_parent_id
ON places(parent_id);

-- Optional: Index für schnellen Zugriff auf relation_type in place_relations
CREATE INDEX IF NOT EXISTS idx_place_relations_type
ON place_relations(relation_type);

-- Optional: Index auf place_id in allen relationalen Tabellen für JOINs
CREATE INDEX IF NOT EXISTS idx_place_aliases_place_id
ON place_aliases(place_id);

CREATE INDEX IF NOT EXISTS idx_place_admin_history_place_id
ON place_admin_history(place_id);

CREATE INDEX IF NOT EXISTS idx_place_religion_history_place_id
ON place_religion_history(place_id);

CREATE INDEX IF NOT EXISTS idx_place_population_place_id
ON place_population(place_id);

CREATE INDEX IF NOT EXISTS idx_place_area_place_id
ON place_area(place_id);

CREATE INDEX IF NOT EXISTS idx_place_sources_place_id
ON place_sources(place_id);


-- ===============================
--   TRIGGER FUNKTION FÜR UPDATED_AT
-- ===============================
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===============================
--   TRIGGER FÜR PLACES
-- ===============================
ALTER TABLE places
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

CREATE TRIGGER trg_places_updated_at
BEFORE UPDATE ON places
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();

-- ===============================
--   OPTIONALE TRIGGER FÜR ALLE RELATIONALEN TABELLEN
-- ===============================

-- Für Tabellen, die updated_at haben sollen, zuerst die Spalte hinzufügen
ALTER TABLE place_aliases ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE place_relations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE place_admin_history ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE place_religion_history ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE place_population ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE place_area ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE place_sources ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Trigger erstellen
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT unnest(ARRAY['place_aliases','place_relations','place_admin_history','place_religion_history','place_population','place_area','place_sources'])
    LOOP
        EXECUTE format('
            CREATE TRIGGER trg_%1$I_updated_at
            BEFORE UPDATE ON %1$I
            FOR EACH ROW
            EXECUTE PROCEDURE trigger_set_timestamp();
        ', tbl);
    END LOOP;
END
$$;

-- ===================================================================
--   test 
-- ===================================================================

SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_name = 'places';