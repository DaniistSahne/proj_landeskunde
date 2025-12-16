-- Datenpfad, Version, Postgisversion überprüfung:

SHOW data_directory;
SELECT version();
SELECT postgis_full_version();

/* Aktivieren von PostGIS für Geo-Funktionalität

CREATE EXTENSION IF NOT EXISTS postgis;

*/

----------------------------------------------------------------

-- neues schema erstellen "x"
CREATE SCHEMA IF NOT EXISTS x;

-- als standardt setzen
SET search_path TO x, public;

--Prüfung
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'landeskunde';


-- Tabellen aus Schema löschen

DROP TABLE IF EXISTS public.tab1 CASCADE;
DROP TABLE IF EXISTS public.tab2 CASCADE;
DROP TABLE IF EXISTS public.tab3 CASCADE;
DROP TABLE IF EXISTS public.tab4 CASCADE;
DROP TABLE IF EXISTS public.tab5 CASCADE;

