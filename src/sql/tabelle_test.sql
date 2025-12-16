-- schema.sql für Ortslexikon
-- Voraussetzung: PostGIS ist bereits aktiviert

-- neues schema erstellen "landeskunde"
CREATE SCHEMA IF NOT EXISTS landeskunde;

-- als standardt setzen
SET search_path TO landeskunde, public;


-- 1. Haupttabelle: Orte
CREATE TABLE IF NOT EXISTS orte (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    kurzname TEXT,                       -- optional kurze Bezeichnung
    alternativenamen JSONB,              -- [{"name":"Arnsfelde","quelle":"Landbuch 1375"}]
    ortstyp TEXT,                        -- z.B. "Dorf", "Gut"
    gemeinde_1900 TEXT,
    eingemeindungen JSONB,               -- [{"jahr":1927,"art":"Eingemeindung","ziel":"Berlin"}]
    gemarkung_1860 NUMERIC,
    gemarkung_1900 NUMERIC,
    gemarkung_1931 NUMERIC,
    siedlungsform TEXT,
    flurnamen TEXT,
    erste_erwaehnung INT,
    quelle_erwaehnung TEXT,
    gerichtsbarkeit JSONB,               -- [{"jahr_von":1849,"jahr_bis":1879,"gericht":"Kreisgericht Berlin"}]
    wirtschaft JSONB,                    -- strukturierte agrarwirtschaftliche Daten
    kirche JSONB,                        -- kirchliche Zuordnungen, Patronate
    baudenkmale JSONB,                   -- [{"titel":"Feldsteinkirche","beschreibung":"..."}]
    beschreibung TEXT,
    geometrie GEOMETRY(Point,4326),      -- Koordinate als Punkt (lon/lat)
    wikidata_id TEXT,                    -- z.B. "Qxxxx"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 2. Bevölkerungsdaten (normalisiert)
CREATE TABLE IF NOT EXISTS bevoelkerung (
    id SERIAL PRIMARY KEY,
    ort_id INT NOT NULL REFERENCES orte(id) ON DELETE CASCADE,
    jahr INT NOT NULL,
    einwohner INT,
    anmerkung TEXT
);

-- 3. Herrschaftsverlauf
CREATE TABLE IF NOT EXISTS herrschaft (
    id SERIAL PRIMARY KEY,
    ort_id INT NOT NULL REFERENCES orte(id) ON DELETE CASCADE,
    besitzer TEXT NOT NULL,
    jahr_von INT,
    jahr_bis INT,
    anmerkung TEXT
);

-- 4. Bilder / Medien
CREATE TABLE IF NOT EXISTS bilder (
    id SERIAL PRIMARY KEY,
    ort_id INT NOT NULL REFERENCES orte(id) ON DELETE CASCADE,
    dateiname TEXT NOT NULL,     -- Pfad oder S3-URL
    titel TEXT,
    typ TEXT,                   -- Foto, Ansicht, Plan, etc.
    quelle TEXT,
    lizenz TEXT,
    beschreibung TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 5. Diagramme / strukturierte Statistik-Daten
CREATE TABLE IF NOT EXISTS diagramme (
    id SERIAL PRIMARY KEY,
    ort_id INT NOT NULL REFERENCES orte(id) ON DELETE CASCADE,
    typ TEXT NOT NULL,          -- "bevoelkerung", "wirtschaft" etc.
    daten JSONB NOT NULL,       -- Chartfreundliche Struktur
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 6. Indizes
-- Geo-Index
CREATE INDEX IF NOT EXISTS idx_orte_geom ON orte USING GIST(geometrie);

-- Volltext-Index (Grundlage; für bessere Suche später Elasticsearch)
CREATE INDEX IF NOT EXISTS idx_orte_name_tsv ON orte USING GIN (to_tsvector('german', coalesce(name,'') || ' ' || coalesce(beschreibung,'')));

-- JSONB-Index-Beispiel für alternativenamen (Suche nach Namen in JSONB)
CREATE INDEX IF NOT EXISTS idx_orte_altname_gin ON orte USING GIN (alternativenamen jsonb_path_ops);

-- Trigger um updated_at zu pflegen
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_orte_updated_at
BEFORE UPDATE ON orte
FOR EACH ROW EXECUTE PROCEDURE trigger_set_timestamp();

-----------------------------------------------------------------------------
-- test tabellen erstellung

-- 1. Alle Tabellen im landeskunde-Schema anzeigen
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'landeskunde';

-- 2. Spalten einer bestimmten Tabelle anzeigen
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'orte';

-- 3. Indizes anzeigen
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'orte';

-- 4. Trigger anzeigen
SELECT tgname, tgtype::integer, tgfoid::regprocedure
FROM pg_trigger
WHERE tgrelid = 'orte'::regclass;

-- 5. PostGIS-Version prüfen
SELECT postgis_full_version();

-----------------------------------------------------------------------------

-- test eintrag_ahrensfelde:
INSERT INTO orte (
    name,
    ortstyp,
    gemeinde_1900,
    erste_erwaehnung,
    geometrie,
    beschreibung
) VALUES (
    'Ahrensfelde',
    'Dorf',
    'Ahrensfelde',
    1375,
    ST_SetSRID(ST_MakePoint(13.5605, 52.5919), 4326),
    'Erstmals 1375 im Landbuch Kaiser Karls IV. erwähnt.'
);

-- kontrolle eintrag_1 / nicht mach
-- SELECT id, name, ST_AsText(geometrie), created_at FROM orte;


-- test eintrag_ahrensfelde:
INSERT INTO bevoelkerung (ort_id, jahr, einwohner, anmerkung)
VALUES (1, 1900, 1245, 'laut Volkszählung 1900');

INSERT INTO herrschaft (ort_id, besitzer, jahr_von, jahr_bis, anmerkung)
VALUES (1, 'Kloster Chorin', 1300, 1539, 'vor der Reformation im Besitz des Klosters');

INSERT INTO bilder (ort_id, dateiname, titel, typ, quelle, lizenz)
VALUES (1, 'ahrensfelde_kirche.jpg', 'Dorfkirche Ahrensfelde', 'Foto', 'Landesarchiv', 'CC-BY');

INSERT INTO diagramme (ort_id, typ, daten)
VALUES (1, 'bevoelkerung', '[{"jahr":1900,"einwohner":1245},{"jahr":1939,"einwohner":1650}]');

-- kontrolle eintrag_2
SELECT * FROM orte;
SELECT * FROM bevoelkerung;
SELECT * FROM herrschaft;
SELECT * FROM bilder;
SELECT * FROM diagramme;

