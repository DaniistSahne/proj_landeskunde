import re
import json
import unicodedata
import psycopg2

# ============================
# Helper
# ============================
def esc(s):
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"

def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().upper()

# ============================
# HOL laden + Blöcke
# ============================
def load_blocks(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = unicodedata.normalize("NFKC", f.read())

    lines = raw.split("\n")
    places = []

    for i, line in enumerate(lines):
        line = line.strip()
        if re.fullmatch(r"[A-ZÄÖÜ0-9' ()\/\-]+", line) and len(line) > 2:
            if not line.lower().startswith("s."):
                places.append((line, i))

    blocks = {}
    for idx, (name, start) in enumerate(places):
        end = places[idx + 1][1] if idx + 1 < len(places) else len(lines)
        blocks[name] = "\n".join(lines[start:end]).strip()

    return blocks

# ============================
# Parser – Punkt 8: Kirche
# ============================
def parse_kirche_smart(block_text):
    m = re.search(r"\b8\.\s+(.*?)(?=\n\s*\d+\.|$)", block_text, re.S)
    if not m:
        return []

    text = re.sub(r"\s*\n\s*", " ", m.group(1))
    years = list(re.finditer(r"\b(1[0-9]{3}|20[0-9]{2})\b", text))

    segments = []
    for i, y in enumerate(years):
        start = y.start()
        end = years[i+1].start() if i+1 < len(years) else len(text)
        seg = text[start:end].strip()

        segments.append({
            "years": [int(x) for x in re.findall(r"\d{4}", seg)],
            "raw": seg
        })

    return segments

# ============================
# SQL Generator
# ============================
def sql_insert_church(place_id, data):
    return f"""
INSERT INTO landeskunde.place_church_history
(place_id, data)
VALUES (
    {place_id},
    {esc(json.dumps(data, ensure_ascii=False))}
);
""".strip()

# ============================
# DB: place_id map
# ============================
def build_place_id_map(conn):
    with conn.cursor() as cur:
        cur.execute("SET search_path TO landeskunde, public;")
        cur.execute("SELECT id, name FROM places")
        return {norm_name(name): pid for pid, name in cur.fetchall()}

# ============================
# Hauptgenerator
# ============================
def generate_church_sql(src_path, out_path, db_dsn):
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

        segments = parse_kirche_smart(block)
        if segments:
            sqls.append(sql_insert_church(place_id, segments))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(sqls))

    print("✔ Kirche SQL erzeugt:", out_path)

# ============================
# Start
# ============================
if __name__ == "__main__":
    generate_church_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\place_church_import.sql",
        db_dsn="dbname=landeskunde_gis user=postgres password=password host=localhost port=5432"
    )
