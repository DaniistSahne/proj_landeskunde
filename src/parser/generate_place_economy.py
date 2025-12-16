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
# Parser – Punkt 7 Wirtschaft
# ============================
def parse_economy(block_text):
    m = re.search(r"\b7\.\s+(.*?)(?=\n\s*\d+\.|$)", block_text, re.S)
    if not m:
        return []

    text = m.group(1).strip()
    parts = re.split(r"(?:(?<=\n)|^)\s*(\d{3,4}[a-z]?)\s*:\s*", text)

    results = []
    last_entry = None

    for i in range(1, len(parts), 2):
        year_raw = parts[i]
        content = parts[i + 1].strip()

        year_clean = year_raw.replace("c", "0").replace("·", "").strip()
        if not year_clean.isdigit():
            continue

        year = int(year_clean)
        entry = {"year": year}

        # dgl. = wie vorher
        if "dgl" in content.lower() and last_entry:
            for k, v in last_entry.items():
                if k != "year":
                    entry[k] = v

        # Gesamt-Hufen
        m_hf = re.search(r"(\d+)\s*Hf\b", content)
        if m_hf:
            entry["Hf_total"] = int(m_hf.group(1))

        # Hufenarten
        hf_details = {}
        for num, key in re.findall(r"(\d+)\s*([A-Za-zÄÖÜäöüß]+Hf[r]?)", content):
            hf_details[key] = int(num)
        if hf_details:
            entry["Hf_details"] = hf_details

        # Berufsgruppen / Zahlen
        for num, name in re.findall(r"(\d+)\s+([A-Za-zÄÖÜäöüß][A-Za-z0-9ÄÖÜäöüß\-]*)", content):
            if name.endswith(("Hf", "Hfr", "PfarrHf", "Hfl")):
                continue
            entry[name] = int(num)

        # Mühlen
        for mname in re.findall(r"\b([A-Za-zÄÖÜäöüß]+mühle)\b", content):
            entry[mname] = True

        # Wüstungen
        wust = re.findall(r"wüste\s+([A-Za-zÄÖÜäöüß]+)", content)
        if wust:
            entry["wüstungen"] = wust

        results.append(entry)
        last_entry = entry

    return results

# ============================
# SQL Generator
# ============================
def sql_insert_economy(place_id, entry):
    import json
    return f"""
INSERT INTO landeskunde.place_economy
(place_id, data)
VALUES (
    {place_id},
    {esc(json.dumps(entry, ensure_ascii=False))}
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
def generate_economy_sql(src_path, out_path, db_dsn):
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

        for entry in parse_economy(block):
            sqls.append(sql_insert_economy(place_id, entry))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(sqls))

    print(f"✔ Wirtschaft SQL erzeugt: {out_path}")

# ============================
# Start
# ============================
if __name__ == "__main__":
    generate_economy_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\place_economy_import.sql",
        db_dsn="dbname=landeskunde_gis user=postgres password=password host=localhost port=5432"
    )
