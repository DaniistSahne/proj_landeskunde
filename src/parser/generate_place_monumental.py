import re
import unicodedata
import psycopg2

# -------------------------------------------------------------------
# Helper
# -------------------------------------------------------------------
def esc(s):
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"

# -------------------------------------------------------------------
# Build place_id map from DB
# -------------------------------------------------------------------
def build_place_id_map(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM places")
        return {name.strip().upper(): pid for pid, name in cur.fetchall()}

# -------------------------------------------------------------------
# Parser – Punkt 9 Baudenkmale
# -------------------------------------------------------------------
def parse_baudenkmale(block_text):
    m = re.search(r"\b9\.\s+(.*?)(?=\n\s*\d+\.|$)", block_text, re.S)
    if not m:
        return []

    text = re.sub(r"\s*\n\s*", " ", m.group(1)).replace("–", "-")
    segments = re.split(r";\s*|\.\s+(?=[A-ZÄÖÜ])", text)

    results = []
    for seg in segments:
        seg = seg.strip().rstrip(".")
        if not seg:
            continue

        m2 = re.match(r"([^,]+),\s*(.*)", seg)
        if m2:
            title, desc = m2.group(1), m2.group(2)
        else:
            title, desc = seg, ""

        results.append({
            "title": title.strip(),
            "description": desc.strip(),
            "notes": None
        })

    return results

# -------------------------------------------------------------------
# SQL Generator
# -------------------------------------------------------------------
def sql_insert_monument(place_id, m):
    return f"""
INSERT INTO place_monuments
(place_id, title, description, notes)
VALUES (
    {place_id},
    {esc(m['title'])},
    {esc(m['description'])},
    {esc(m['notes'])}
);
""".strip()

# -------------------------------------------------------------------
# HOL-Datei laden + Blöcke
# -------------------------------------------------------------------
def load_blocks(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = unicodedata.normalize("NFKC", f.read())

    lines = raw.split("\n")
    places = []

    for i, line in enumerate(lines):
        if re.fullmatch(r"[A-ZÄÖÜ0-9' ()\/\-]+", line.strip()):
            places.append((line.strip(), i))

    blocks = {}
    for i, (name, start) in enumerate(places):
        end = places[i+1][1] if i+1 < len(places) else len(lines)
        blocks[name] = "\n".join(lines[start:end]).strip()

    return blocks

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
def generate_monuments_sql(src_path, out_path, db_dsn):
    # --- DB Connection ---
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

        for m in parse_baudenkmale(block):
            sqls.append(sql_insert_monument(place_id, m))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(sqls))

    print("✔ Baudenkmale SQL erzeugt:", out_path)

# -------------------------------------------------------------------
# START
# -------------------------------------------------------------------
if __name__ == "__main__":
    generate_monuments_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\place_monuments_import.sql",
        db_dsn="dbname=landeskunde_gis user=postgres password=password host=localhost port=5432"
    )
