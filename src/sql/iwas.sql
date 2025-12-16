SET search_path TO landeskunde, public;

select * from orte;

SELECT id, name, ortstyp, gemeinde_1900, erste_erwaehnung
FROM landeskunde.orte
WHERE name ILIKE '%ahrensfelde%';



delete from orte
where id = 1;

-- automatische ID aufpassen => überprüfen und ändern später

/*

update orte
set id = 1
where id = 2;
select * from orte;

-- update der ID 2 zu 1 
-- shortcut für auskommentierung suchen

*/


