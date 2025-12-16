import re
import unicodedata
import psycopg2
import json

# ============================
# Hilfsfunktion für SQL-escaping
# ============================
def esc(s):
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"

# ============================
# Ortsnamen normalisieren
# ============================
def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().upper()

# ============================
# HOL-Datei laden + Blöcke schneiden
# ============================
def load_blocks(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    clean = unicodedata.normalize("NFKC", raw)
    lines = clean.split("\n")
    places = []

    # Ortsüberschriften finden (GROSS, kein "s.")
    for i, line in enumerate(lines):
        line = line.strip()
        if re.fullmatch(r"[A-ZÄÖÜ0-9' ()\/\-]+", line) and len(line) > 2:
            if not line.lower().startswith("s."):
                places.append((line, i))

    # Blöcke schneiden
    blocks = {}
    for idx, (place, start) in enumerate(places):
        end = places[idx + 1][1] if idx + 1 < len(places) else len(lines)
        block = "\n".join(lines[start:end]).strip()
        blocks[place] = block

    return blocks

# ============================
# Parser: Flächenangaben (Punkt 2)
# ============================
def parse_area_generic(block_text):
    m = re.search(r"\b2\.\s+(.*?)(?=\n\s*\d+\.)", block_text, re.S)
    if not m:
        return []

    text = m.group(1)
    entries = []

    # Muster: "1375: 9450 Mg (300 Mg Acker, 200 Mg Wiesen...)"
    pattern = r"(\d{3,4})\s*:\s*([\d\s]+)\s*(Mg|ha)(?:\s*\((.*?)\))?"
    matches = re.findall(pattern, text, re.S)

    for year, total, unit, details in matches:
        total_clean = int(total.replace(" ", ""))
        row = {
            "year": int(year),
            "area_total": total_clean,
            "unit": unit,
            "categories": {}   # wird zu JSONB konvertiert
        }

        # Falls Kategorien existieren
        if details:
            # z.B. "360 Mg Gehöfte, 72 Mg Gartenland..."
            parts = re.findall(r"(\d[\d\s]*)\s*Mg\s+([A-Za-zäöüÄÖÜß]+)", details)
            for value, category_name in parts:
                val_clean = int(value.replace(" ", ""))
                row["categories"][category_name] = val_clean

        entries.append(row)

    return entries

# ============================
# SQL Generator
# ============================
def sql_insert_area(place_id, row):
    return f"""
INSERT INTO landeskunde.place_area
(place_id, year, area_total, unit, categories)
VALUES (
    {place_id},
    {row['year']},
    {row['area_total']},
    {esc(row['unit'])},
    {esc(json.dumps(row['categories'], ensure_ascii=False))}
);
""".strip()

# ============================
# DB: place_id map aufbauen
# ============================
def build_place_id_map(conn):
    with conn.cursor() as cur:
        cur.execute("SET search_path TO landeskunde, public;")
        cur.execute("SELECT id, name FROM places")
        return {norm_name(name): pid for pid, name in cur.fetchall()}

# ============================
# Hauptgenerator
# ============================
def generate_area_sql(src_path, out_path="place_area_import.sql", db_dsn=None):
    if db_dsn is None:
        raise ValueError("db_dsn muss angegeben werden!")

    # DB-Verbindung
    conn = psycopg2.connect(db_dsn)
    place_id_map = build_place_id_map(conn)
    conn.close()

    blocks = load_blocks(src_path)
    sqls = []

    # Header: search_path
    sqls.append("SET search_path TO landeskunde, public;")

    for place_name, block in blocks.items():
        key = norm_name(place_name)
        place_id = place_id_map.get(key)
        if place_id is None:
            print(f"⚠️ Ort NICHT in DB: {place_name}")
            continue

        area_entries = parse_area_generic(block)
        for entry in area_entries:
            sqls.append(sql_insert_area(place_id, entry))

    # Speichern
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sqls))

    print(f"[OK] Flächen-SQL gespeichert unter: {out_path}")

# ============================
# Start
# ============================
if __name__ == "__main__":
    generate_area_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\place_area_import.sql",
        db_dsn="dbname=landeskunde_gis user=postgres password=password host=localhost port=5432"
    )
