-- 1. Temporäre Tabelle erstellen
SET search_path TO landeskunde, public;

CREATE TABLE place_alias_temp (
    place_name text,
    alias text,
    year_from int,
    year_to int,
    source text
);

-- 2. Temp-SQL ausführen
\i 'aliases_temp.sql';

-- 3. Aliase mit place_id verbinden
INSERT INTO place_aliases (place_id, alias, year_from, year_to, source)
SELECT p.id, t.alias, t.year_from, t.year_to, t.source
FROM place_alias_temp t
JOIN places p ON UPPER(p.name) = UPPER(t.place_name)
ORDER BY p.id;
