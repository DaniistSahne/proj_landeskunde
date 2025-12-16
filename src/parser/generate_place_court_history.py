import re
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
# HOL-Datei laden + Blöcke schneiden
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
# Parser für Gerichtshistorie (Punkt 5)
# ============================
def parse_court_history(text):
    # 1) Finde Punkt 5
    m = re.search(r"5\.\s*(.*?)(?=\n\s*\d+\.|$)", text, flags=re.S)
    if not m:
        return []

    raw = m.group(1).replace("\n", " ")

    # 2) Split an Kommas/Semikolons
    parts = re.split(r"[;,]\s*", raw)

    entries = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # "Bis 1849 ..."
        m1 = re.match(r"Bis\s+(\d{4})\s+(.*)", part)
        if m1:
            year_to = int(m1.group(1))
            rest = m1.group(2)
            tokens = rest.split(maxsplit=1)
            court_type = tokens[0]
            court_name = rest
            entries.append({
                "year_from": None,
                "year_to": year_to,
                "court_type": court_type,
                "court_name": court_name
            })
            continue

        # "1849–1878 ..."
        m2 = re.match(r"(\d{4})\s*[-–]\s*(\d{4})\s+(.*)", part)
        if m2:
            yf = int(m2.group(1))
            yt = int(m2.group(2))
            rest = m2.group(3)
            tokens = rest.split(maxsplit=1)
            court_type = tokens[0]
            court_name = rest
            entries.append({
                "year_from": yf,
                "year_to": yt,
                "court_type": court_type,
                "court_name": court_name
            })
            continue

        # fallback: keine Jahre
        entries.append({
            "year_from": None,
            "year_to": None,
            "court_type": "",
            "court_name": part
        })

    return entries

# ============================
# SQL Generator
# ============================
def sql_insert_court(place_id, entry):
    year_from = "NULL" if entry["year_from"] is None else entry["year_from"]
    year_to   = "NULL" if entry["year_to"]   is None else entry["year_to"]
    court_type = esc(entry["court_type"])
    court_name = esc(entry["court_name"])

    return (
        "INSERT INTO place_court_history (place_id, year_from, year_to, court_name, court_type, notes) "
        f"VALUES ({place_id}, {year_from}, {year_to}, {court_name}, {court_type}, '');"
    )

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
def generate_court_sql(src_path, out_path, db_dsn):
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

        entries = parse_court_history(block)
        for e in entries:
            sqls.append(sql_insert_court(place_id, e))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sqls))

    print(f"✔ Gerichtshistorie SQL erzeugt: {out_path}")

# ============================
# Start
# ============================
if __name__ == "__main__":
    generate_court_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\court_history_import.sql",
        db_dsn="dbname=landeskunde_gis user=postgres password=password host=localhost port=5432"
    )
