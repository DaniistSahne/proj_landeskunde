import re
import unicodedata
import psycopg2

# =========================================================
# Hilfsfunktionen
# =========================================================
def esc(s):
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"

def clean_number(s):
    """Repariert typische OCR-Fehler in Zahlen."""
    replacements = {
        'G': '6', 'E': '6',
        'L': '1', 'l': '1',
        'O': '0'
    }
    for bad, good in replacements.items():
        s = s.replace(bad, good)
    return re.sub(r"[^\d]", "", s)

# =========================================================
# Parser – Punkt 10 Bevölkerung
# =========================================================
def parse_bevoelkerung_advanced(block_text):
    m = re.search(r"\b10\.\s+(.*?)(?=\n\s*\d+\.|$)", block_text, re.S)
    if not m:
        return []

    text = m.group(1)
    raw_entries = re.findall(r"(\d{3,4}(?:[-/]\d{2,4})?)\s*:\s*([^:,]+)", text)

    results = []
    for raw_year, raw_value in raw_entries:
        year_str = clean_number(raw_year)
        if "-" in year_str:
            year_str = year_str.split("-")[0]

        try:
            year = int(year_str)
        except ValueError:
            continue

        nums = re.findall(r"\d[\d\s]*", raw_value)
        if not nums:
            continue

        inhabitants = int(clean_number(nums[0]))

        results.append({
            "year": year,
            "inhabitants": inhabitants,
            "notes": raw_value.strip()
        })

    return results

# =========================================================
# HOL-Datei → Blöcke
# =========================================================
def load_blocks(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = unicodedata.normalize("NFKC", f.read())

    lines = raw.split("\n")
    places = []
    for i, line in enumerate(lines):
        line = line.strip()
        if re.fullmatch(r"[A-ZÄÖÜ0-9' ()\/\-]+", line):
            if len(line) > 2 and not line.lower().startswith("s."):
                places.append((line, i))

    blocks = {}
    for idx, (place, start) in enumerate(places):
        end = places[idx + 1][1] if idx + 1 < len(places) else len(lines)
        blocks[place] = "\n".join(lines[start:end]).strip()

    return blocks

# =========================================================
# SQL-Generator
# =========================================================
def sql_insert_population(place_id, entry):
    return f"""
INSERT INTO place_population
(place_id, year, inhabitants, notes)
VALUES (
    {place_id},
    {entry['year']},
    {entry['inhabitants']},
    {esc(entry.get('notes'))}
);
""".strip()

# =========================================================
# DB: place_id_map
# =========================================================
def build_place_id_map(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM places")
        return {name.strip().upper(): pid for pid, name in cur.fetchall()}

# =========================================================
# MAIN
# =========================================================
def generate_population_sql(src_path, out_path, db_dsn):
    # --- DB connect ---
    conn = psycopg2.connect(db_dsn, options="-c search_path=landeskunde,public")
    place_id_map = build_place_id_map(conn)
    conn.close()

    blocks = load_blocks(src_path)
    sqls = []

    for place_name, block in blocks.items():
        key = place_name.strip().upper()
        place_id = place_id_map.get(key)
        if place_id is None:
            print(f"⚠️ Ort NICHT in DB: {place_name}")
            continue

        entries = parse_bevoelkerung_advanced(block)
        for e in entries:
            sqls.append(sql_insert_population(place_id, e))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sqls))

    print(f"✔ Bevölkerung SQL erzeugt: {len(sqls)} Einträge → {out_path}")

# =========================================================
# START
# =========================================================
if __name__ == "__main__":
    generate_population_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\population_import.sql",
        db_dsn="dbname=landeskunde_gis user=postgres password=password host=localhost port=5432"
    )
