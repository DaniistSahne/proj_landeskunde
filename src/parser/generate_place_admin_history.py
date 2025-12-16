import re
import unicodedata
import psycopg2

# ============================
# 1) NORMALISIERUNG
# ============================
def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().upper()


# ============================
# 2) HOL-Datei einlesen + Blöcke
# ============================
def load_blocks(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    clean = unicodedata.normalize("NFKC", raw)
    lines = clean.split("\n")

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


# ============================
# 3) Verwaltungsgeschichte parsen
# ============================
def parse_admin(block_text):
    lines = block_text.split("\n")

    # Verwaltungseintrag finden (erste Zeile mit "-")
    admin_line = None
    for line in lines:
        if " - " in line:
            admin_line = line.strip().rstrip(".")
            break

    if not admin_line:
        return []

    # Teile an " - "
    parts = [p.strip() for p in admin_line.split(" - ")]
    results = []

    # --- Phase 1: vor 1816 ---
    results.append({
        "year_from": None,
        "year_to": 1815,
        "admin_unit": parts[0],
        "admin_level": "Kreis",
        "notes": ""
    })

    # --- Phase 2: 1816–1951 ---
    if len(parts) > 1:
        results.append({
            "year_from": 1816,
            "year_to": 1951,
            "admin_unit": parts[1],
            "admin_level": "Kreis",
            "notes": ""
        })

    # --- Phase 3: ab 1952 ---
    if len(parts) > 2:
        sub = [p.strip() for p in re.split(r"/", parts[2])]
        for s in sub:
            if s.startswith("Kr "):
                results.append({
                    "year_from": 1952,
                    "year_to": 1990,
                    "admin_unit": s[3:].strip(),
                    "admin_level": "Kreis",
                    "notes": ""
                })
            elif s.startswith("Bez "):
                results.append({
                    "year_from": 1952,
                    "year_to": 1990,
                    "admin_unit": s[4:].strip(),
                    "admin_level": "Bezirk",
                    "notes": ""
                })
            else:
                results.append({
                    "year_from": 1952,
                    "year_to": 1990,
                    "admin_unit": s,
                    "admin_level": "Unbekannt",
                    "notes": ""
                })

    return results


# ============================
# 4) SQL-escaping
# ============================
def esc(s):
    if s is None:
        return ""
    return str(s).replace("'", "''")


# ============================
# 5) place_id Map aus DB
# ============================
def build_place_id_map(conn):
    with conn.cursor() as cur:
        # search_path setzen
        cur.execute("SET search_path TO landeskunde, public")
        cur.execute("SELECT id, name FROM places")
        return {norm_name(name): pid for pid, name in cur.fetchall()}


# ============================
# 6) SQL-Generator
# ============================
def sql_insert_admin(place_id, entry):
    year_from = "NULL" if entry["year_from"] is None else entry["year_from"]
    year_to   = "NULL" if entry["year_to"]   is None else entry["year_to"]
    admin_unit = esc(entry["admin_unit"])
    admin_level = esc(entry["admin_level"])
    notes = esc(entry["notes"])

    sql = (
        f"INSERT INTO place_admin_history "
        f"(place_id, year_from, year_to, admin_unit, admin_level, notes) "
        f"VALUES ({place_id}, {year_from}, {year_to}, '{admin_unit}', '{admin_level}', '{notes}');"
    )
    return sql


# ============================
# 7) Hauptfunktion
# ============================
def generate_admin_sql(src_path, out_path, db_dsn):
    conn = psycopg2.connect(db_dsn)
    place_id_map = build_place_id_map(conn)
    blocks = load_blocks(src_path)
    sqls = []

    for place_name, block in blocks.items():
        key = norm_name(place_name)
        place_id = place_id_map.get(key)
        if place_id is None:
            print(f"⚠️ Ort NICHT in DB: {place_name}")
            continue

        entries = parse_admin(block)
        for e in entries:
            sqls.append(sql_insert_admin(place_id, e))

    conn.close()

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sqls))

    print(f"✅ Fertig! SQL gespeichert unter: {out_path}")


# ============================
# 8) START
# ============================
if __name__ == "__main__":
    generate_admin_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\admin_history_import.sql",
        db_dsn="dbname=landeskunde_gis user=postgres password=password host=localhost"
    )
