# --- Begin: generate_places_sql.py ---
import json
import re
import unicodedata

# -------------------------------------------------------------------
# Helper
# -------------------------------------------------------------------

def esc(s):
    """Escape quotes for SQL."""
    if s is None:
        return "NULL"
    if isinstance(s, str):
        return "'" + s.replace("'", "''") + "'"
    return str(s)

# -------------------------------------------------------------------
# EXTRACTORS – echte Version
# -------------------------------------------------------------------

# 1. Typ (z.B. Dorf, Stadt...)
def extract_type(block: str):
    m = re.search(r"\b1\.\s*([A-Za-zÄÖÜäöüß\- ]+)", block)
    return m.group(1).strip() if m else None

# 3. Siedlungsform
def extract_settlement_type(block: str):
    m = re.search(r"\b3\.\s*([A-Za-zÄÖÜäöüß\- ]+)", block)
    return m.group(1).strip() if m else None

# 4. Jahr der Ersterwähnung
def extract_first_mention_year(block: str):
    m = re.search(r"\b4\.\s*(\d{3,4})", block)
    return int(m.group(1)) if m else None

# 4. Quelle hinter Klammer
def extract_first_mention_source(block: str):
    m = re.search(r"\b4\.[^\(]*\(([^)]+)\)", block)
    return m.group(1).strip() if m else None

# Lagehinweis (zweite Zeile des Blocks)
def extract_lage_hinweis(block: str):
    lines = block.strip().splitlines()
    if len(lines) >= 2:
        return lines[1].strip()
    return None

# Alternative Namen
def extract_alt_names(block: str):
    # Beispiel: "auch Arnsfelde", "früher Arnsfelt"
    names = re.findall(r"\b(?:auch|früher|alias)\s+([A-Za-zÄÖÜäöüß\-]+)", block)
    return names if names else []

# -------------------------------------------------------------------
# Hauptparser
# -------------------------------------------------------------------

def parse_place(block: str):
    return {
        "type": extract_type(block),
        "settlement_type": extract_settlement_type(block),
        "first_mention_year": extract_first_mention_year(block),
        "first_mention_source": extract_first_mention_source(block),
        "lage_hinweis": extract_lage_hinweis(block),
        "alt_names": extract_alt_names(block),
    }

# -------------------------------------------------------------------
# SQL Generator für die Haupttabelle
# -------------------------------------------------------------------

def sql_insert_place(place_id, place_name, block):
    d = parse_place(block)

    sql = f"""
INSERT INTO landeskunde.places
(place_id, name, type, parent_id, alt_names, settlement_type,
 first_mention_year, first_mention_source, description, lage_hinweis)
VALUES (
    {place_id},
    {esc(place_name)},
    {esc(d['type'])},
    NULL,
    {esc(json.dumps(d['alt_names'], ensure_ascii=False))},
    {esc(d['settlement_type'])},
    {d['first_mention_year'] if d['first_mention_year'] else "NULL"},
    {esc(d['first_mention_source'])},
    {esc(block)},
    {esc(d['lage_hinweis'])}
);
""".strip()

    return sql

# -------------------------------------------------------------------
# HOL-Datei laden + Blöcke schneiden
# -------------------------------------------------------------------

def load_blocks(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    clean = unicodedata.normalize("NFKC", raw)
    lines = clean.split("\n")
    places = []

    # Überschriften finden
    for i, line in enumerate(lines):
        line = line.strip()
        if re.fullmatch(r"[A-ZÄÖÜ0-9' ()\/\-]+", line):
            if len(line) > 2 and not line.lower().startswith("s."):
                places.append((line, i))

    blocks = {}
    for idx, (place, start) in enumerate(places):
        end = places[idx + 1][1] if idx + 1 < len(places) else len(lines)
        block = "\n".join(lines[start:end]).strip()
        blocks[place] = block

    return blocks

# -------------------------------------------------------------------
# SQL-Datei generieren
# -------------------------------------------------------------------

def generate_places_sql(src_path, out_path):
    blocks = load_blocks(src_path)
    sqls = []

    for idx, (place_name, block) in enumerate(blocks.items(), start=1):
        sqls.append(sql_insert_place(idx, place_name, block))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(sqls))

    print("✔ FERTIG! SQL gespeichert unter:", out_path)

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

if __name__ == "__main__":
    generate_places_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\places_import.sql"
    )

# --- End: generate_places_sql.py ---

# --- Begin: generate_aliases_sql.py ---
import re
import unicodedata
import json

# ----------------------------
# 1) BLOCK-SCHNEIDER
# ----------------------------
def load_blocks(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    clean = unicodedata.normalize("NFKC", raw)
    lines = clean.split("\n")

    places = []
    for i, line in enumerate(lines):
        if re.fullmatch(r"[A-ZÄÖÜ0-9' ()\/\-]+", line.strip()):
            places.append((line.strip(), i))

    blocks = {}
    for idx, (place, start) in enumerate(places):
        end = places[idx + 1][1] if idx + 1 < len(places) else len(lines)
        block = "\n".join(lines[start:end])
        blocks[place] = block

    return blocks


# ----------------------------
# 2) ALIAS-PARSER
# ----------------------------
def parse_aliases(block_text):
    p4 = re.search(r"4\.\s*(.+?)(?=\n\d+\.)", block_text, flags=re.S)
    if not p4:
        return []

    content = p4.group(1).strip()
    raw_items = [x.strip() for x in re.split(r"\)\s*,", content)]

    aliases = []

    for item in raw_items:
        m = re.match(r"(\d{3,4})\s+(.+?)\s*\((.*?)\)", item)
        if not m:
            continue

        year = int(m.group(1))
        names_str = m.group(2)
        source = m.group(3).strip()

        names = [x.strip() for x in names_str.split(",")]

        for alias_name in names:
            aliases.append({
                "alias": alias_name,
                "year_from": year,
                "year_to": None,
                "source": source
            })

    return aliases


# ----------------------------
# 3) SQL-GENERATOR
# ----------------------------
def esc(s):
    return s.replace("'", "''")


def sql_insert_alias(place_id, a):
    return (
        "INSERT INTO place_aliases (place_id, alias, year_from, year_to, source) "
        f"VALUES ({place_id}, "
        f"'{esc(a['alias'])}', "
        f"{a['year_from']}, "
        f"NULL, "
        f"'{esc(a['source'])}');"
    )


# ----------------------------
# 4) MAIN
# ----------------------------
def generate_alias_sql(src_path, out_path):
    blocks = load_blocks(src_path)

    sql_lines = []
    for idx, (place_name, block) in enumerate(blocks.items(), start=1):
        aliases = parse_aliases(block)
        for a in aliases:
            sql_lines.append(sql_insert_alias(idx, a))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_lines))

    print("FERTIG: Aliases gespeichert unter:", out_path)


# ----------------------------
# 5) START
# ----------------------------
if __name__ == "__main__":
    generate_alias_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\aliases_import.sql"
    )

# --- End: generate_aliases_sql.py ---

# --- Begin: generate_place_admin.py ---
import re
import unicodedata

# -------------------------------------------------------------------
# Helper
# -------------------------------------------------------------------

def esc(s):
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"

# -------------------------------------------------------------------
# Parser – Punkt 4 Verwaltung
# (LOGIK UNVERÄNDERT)
# -------------------------------------------------------------------

def parse_admin(block_text):
    m = re.search(r"\b4\.\s+(.*?)(?=\n\s*\d+\.|$)", block_text, re.S)
    if not m:
        return []

    admin_raw = m.group(1).strip()
    line = admin_raw.split("\n")[0].rstrip(" .")

    parts = [p.strip() for p in line.split(" - ")]
    results = []

    # Phase 1: vor 1816
    if len(parts) > 0:
        results.append({
            "year_from": None,
            "year_to": 1815,
            "admin_unit": parts[0],
            "admin_level": "Kreis" if parts[0].startswith("Kr ") else "Unbekannt",
            "notes": ""
        })

    # Phase 2: 1816–1951
    if len(parts) > 1:
        results.append({
            "year_from": 1816,
            "year_to": 1951,
            "admin_unit": parts[1],
            "admin_level": "Kreis" if parts[1].startswith("Kr ") else "Unbekannt",
            "notes": ""
        })

    # Phase 3: ab 1952
    if len(parts) > 2:
        for s in re.split(r"/", parts[2]):
            s = s.strip()
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

# -------------------------------------------------------------------
# SQL Generator
# -------------------------------------------------------------------

def sql_insert_admin(place_id, a):
    return f"""
INSERT INTO landeskunde.place_admin
(place_id, year_from, year_to, admin_unit, admin_level, notes)
VALUES (
    {place_id},
    {a['year_from'] if a['year_from'] else "NULL"},
    {a['year_to'] if a['year_to'] else "NULL"},
    {esc(a['admin_unit'])},
    {esc(a['admin_level'])},
    {esc(a['notes'])}
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
        line = line.strip()
        if re.fullmatch(r"[A-ZÄÖÜ0-9' ()\/\-]+", line):
            places.append((line, i))

    blocks = {}
    for i, (name, start) in enumerate(places):
        end = places[i + 1][1] if i + 1 < len(places) else len(lines)
        blocks[name] = "\n".join(lines[start:end]).strip()

    return blocks

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

def generate_admin_sql(src_path, out_path):
    blocks = load_blocks(src_path)
    sql = []

    for place_id, block in enumerate(blocks.values(), start=1):
        for entry in parse_admin(block):
            sql.append(sql_insert_admin(place_id, entry))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(sql))

    print("✔ place_admin SQL erzeugt:", out_path)

if __name__ == "__main__":
    generate_admin_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\place_admin_import.sql"
    )

# --- End: generate_place_admin.py ---

# --- Begin: generate_place_admin_history.py ---
import re
import unicodedata

# === Hilfsfunktion für SQL-escaping =================================================
def esc(s):
    if s is None:
        return ""
    return str(s).replace("'", "''")

# === HOL-Datei einlesen und Blöcke schneiden =======================================
def load_blocks(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    # Unicode normalisieren
    clean = unicodedata.normalize("NFKC", raw)
    lines = clean.split("\n")
    places = []

    # Ortsüberschriften finden
    for i, line in enumerate(lines):
        line = line.strip()
        if re.fullmatch(r"[A-ZÄÖÜ0-9' ()\/\-]+", line):
            if len(line) > 2 and not line.lower().startswith("s."):
                places.append((line, i))

    # Blöcke schneiden
    blocks = {}
    for idx, (place, start) in enumerate(places):
        end = places[idx + 1][1] if idx + 1 < len(places) else len(lines)
        block = "\n".join(lines[start:end]).strip()
        blocks[place] = block

    return blocks

# === Parser für Verwaltungsgeschichte ===========================================
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
    results.append({
        "year_from": 1816,
        "year_to": 1951,
        "admin_unit": parts[1],
        "admin_level": "Kreis",
        "notes": ""
    })

    # --- Phase 3: ab 1952 ---
    last = parts[2] if len(parts) > 2 else ""
    sub = [p.strip() for p in re.split(r"[\/]", last)]

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

# === SQL-Generator für Verwaltung =================================================
def sql_insert_admin(place_id, entry):
    year_from = "NULL" if entry["year_from"] is None else entry["year_from"]
    year_to   = "NULL" if entry["year_to"]   is None else entry["year_to"]
    admin_unit = esc(entry["admin_unit"])
    admin_level = esc(entry["admin_level"])
    notes = esc(entry["notes"])

    sql = (
        "INSERT INTO place_admin_history (place_id, year_from, year_to, admin_unit, admin_level, notes) "
        f"VALUES ({place_id}, {year_from}, {year_to}, '{admin_unit}', '{admin_level}', '{notes}');"
    )
    return sql

# === Hauptfunktion zur SQL-Generierung ==========================================
def generate_admin_sql(src_path, out_path="admin_history_import.sql"):
    blocks = load_blocks(src_path)
    sqls = []

    for idx, (place_name, block) in enumerate(blocks.items(), start=1):
        entries = parse_admin(block)
        for e in entries:
            sqls.append(sql_insert_admin(idx, e))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sqls))

    print(f"FERTIG! SQL gespeichert unter: {out_path}")

# === START =======================================================================
if __name__ == "__main__":
    generate_admin_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\admin_history_import.sql"
    )

# --- End: generate_place_admin_history.py ---

# --- Begin: generate_place_area.py ---
import re
import unicodedata

# ======================================================================
#  Hilfsfunktion
# ======================================================================
def esc(s):
    if s is None:
        return ""
    return str(s).replace("'", "''")


# ======================================================================
#  HOL-Datei laden + Blöcke schneiden
# ======================================================================
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


# ======================================================================
#  Parser: Flächenangaben (Punkt 2)
# ======================================================================
def parse_area_generic(block_text):
    """
    Extrahiert:
    - Jahr
    - Gesamtfläche
    - Einheit (Mg, ha)
    - optionale Unterkategorien (Acker, Wiesen, Gehöfte...)

    Rückgabe: Liste von dicts
    """

    # Punkt 2 isolieren
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


# ======================================================================
#  SQL Generator
# ======================================================================
def sql_insert_area(place_id, row):
    year = row["year"]
    total = row["area_total"]
    unit = esc(row["unit"])

    # Unterkategorien als JSON
    import json
    categories_json = esc(json.dumps(row["categories"], ensure_ascii=False))

    sql = (
        "INSERT INTO place_area (place_id, year, area_total, unit, categories) "
        f"VALUES ({place_id}, {year}, {total}, '{unit}', '{categories_json}');"
    )
    return sql


# ======================================================================
#  Gesamtgenerator
# ======================================================================
def generate_area_sql(src_path, out_path="place_area_import.sql"):
    blocks = load_blocks(src_path)
    sqls = []

    for idx, (place_name, block) in enumerate(blocks.items(), start=1):
        area_entries = parse_area_generic(block)
        for entry in area_entries:
            sqls.append(sql_insert_area(idx, entry))

    # Speichern
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sqls))

    print(f"[OK] Flächen-SQL gespeichert unter: {out_path}")


# ======================================================================
#  Startpunkt
# ======================================================================
if __name__ == "__main__":
    generate_area_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\place_area_import.sql"
    )

# --- End: generate_place_area.py ---

# --- Begin: generate_place_church.py ---
import re
import json
import unicodedata

# -------------------------------------------------------------------
# Helper
# -------------------------------------------------------------------

def esc(s):
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"

# -------------------------------------------------------------------
# Parser – Punkt 8
# -------------------------------------------------------------------

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

# -------------------------------------------------------------------
# SQL Generator
# -------------------------------------------------------------------

def sql_insert_church(place_id, data):
    return f"""
INSERT INTO landeskunde.place_religion_history
(place_id, data)
VALUES (
    {place_id},
    {esc(json.dumps(data, ensure_ascii=False))}
);
""".strip()

# -------------------------------------------------------------------
# HOL laden + Blöcke
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

def generate_church_sql(src, out):
    blocks = load_blocks(src)
    sql = []

    for pid, block in enumerate(blocks.values(), start=1):
        segments = parse_kirche_smart(block)
        if segments:
            sql.append(sql_insert_church(pid, segments))

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n\n".join(sql))

    print("✔ Kirche SQL erzeugt:", out)

if __name__ == "__main__":
    generate_church_sql(
        src=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\place_church_import.sql"
    )

# --- End: generate_place_church.py ---

# --- Begin: generate_place_court_history.py ---
import re
import unicodedata

# === Hilfsfunktion für SQL-escaping =================================================
def esc(s):
    if s is None:
        return ""
    return str(s).replace("'", "''")

# === HOL-Datei einlesen und Blöcke schneiden =======================================
def load_blocks(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    # Unicode normalisieren
    clean = unicodedata.normalize("NFKC", raw)
    lines = clean.split("\n")
    places = []

    # Ortsüberschriften finden
    for i, line in enumerate(lines):
        line = line.strip()
        if re.fullmatch(r"[A-ZÄÖÜ0-9' ()\/\-]+", line):
            if len(line) > 2 and not line.lower().startswith("s."):
                places.append((line, i))

    # Blöcke schneiden
    blocks = {}
    for idx, (place, start) in enumerate(places):
        end = places[idx + 1][1] if idx + 1 < len(places) else len(lines)
        block = "\n".join(lines[start:end]).strip()
        blocks[place] = block

    return blocks

# === Parser für Gerichtshistorie (Punkt 5) ========================================
def parse_court_history(text):
    # 1) Finde Punkt 5
    m = re.search(r"5\.\s*(.*?)\n(?=\d+\.|$)", text, flags=re.S)
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

# === SQL-Generator ===============================================================
def sql_insert_court(place_id, entry):
    year_from = "NULL" if entry["year_from"] is None else entry["year_from"]
    year_to   = "NULL" if entry["year_to"]   is None else entry["year_to"]
    court_type = esc(entry["court_type"])
    court_name = esc(entry["court_name"])

    sql = (
        "INSERT INTO place_court_history (place_id, year_from, year_to, court_name, court_type, notes) "
        f"VALUES ({place_id}, {year_from}, {year_to}, '{court_name}', '{court_type}', '');"
    )
    return sql

# === Hauptfunktion zur SQL-Generierung ==========================================
def generate_court_sql(src_path, out_path="court_history_import.sql"):
    blocks = load_blocks(src_path)
    sqls = []

    for idx, (place_name, block) in enumerate(blocks.items(), start=1):
        entries = parse_court_history(block)
        for e in entries:
            sqls.append(sql_insert_court(idx, e))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sqls))

    print(f"FERTIG! SQL gespeichert unter: {out_path}")

# === START =======================================================================
if __name__ == "__main__":
    generate_court_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\court_history_import.sql"
    )

# --- End: generate_place_court_history.py ---

# --- Begin: generate_place_economy.py ---
import re
import json
import unicodedata

# -------------------------------------------------------------------
# Helper
# -------------------------------------------------------------------

def esc(s):
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"

# -------------------------------------------------------------------
# Parser – Punkt 7 Wirtschaft
# -------------------------------------------------------------------

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

        year_clean = (
            year_raw.replace("c", "0")
                    .replace("·", "")
                    .strip()
        )

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
        for num, name in re.findall(
            r"(\d+)\s+([A-Za-zÄÖÜäöüß][A-Za-z0-9ÄÖÜäöüß\-]*)",
            content
        ):
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

# -------------------------------------------------------------------
# SQL Generator
# -------------------------------------------------------------------

def sql_insert_economy(place_id, entry):
    return f"""
INSERT INTO landeskunde.place_economy
(place_id, year, data)
VALUES (
    {place_id},
    {entry['year']},
    {esc(json.dumps(entry, ensure_ascii=False))}
);
""".strip()

# -------------------------------------------------------------------
# HOL laden + Blöcke
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
        end = places[i + 1][1] if i + 1 < len(places) else len(lines)
        blocks[name] = "\n".join(lines[start:end]).strip()

    return blocks

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

def generate_economy_sql(src, out):
    blocks = load_blocks(src)
    sql = []

    for pid, block in enumerate(blocks.values(), start=1):
        for entry in parse_economy(block):
            sql.append(sql_insert_economy(pid, entry))

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n\n".join(sql))

    print("✔ Wirtschaft SQL erzeugt:", out)

if __name__ == "__main__":
    generate_economy_sql(
        src=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\place_economy_import.sql"
    )

# --- End: generate_place_economy.py ---

# --- Begin: generate_place_monumental.py ---
import re
import unicodedata

# -------------------------------------------------------------------
# Helper
# -------------------------------------------------------------------

def esc(s):
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"

# -------------------------------------------------------------------
# Parser – Punkt 9
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
INSERT INTO landeskunde.place_monuments
(place_id, title, description, notes)
VALUES (
    {place_id},
    {esc(m['title'])},
    {esc(m['description'])},
    {esc(m['notes'])}
);
""".strip()

# -------------------------------------------------------------------
# HOL laden + Blöcke
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

def generate_monuments_sql(src, out):
    blocks = load_blocks(src)
    sql = []

    for pid, block in enumerate(blocks.values(), start=1):
        for m in parse_baudenkmale(block):
            sql.append(sql_insert_monument(pid, m))

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n\n".join(sql))

    print("✔ Baudenkmale SQL erzeugt:", out)

if __name__ == "__main__":
    generate_monuments_sql(
        src=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\place_monuments_import.sql"
    )

# --- End: generate_place_monumental.py ---

# --- Begin: generate_place_pop.py ---
# generate_population_sql.py
import re
import unicodedata


# =========================================================
# Hilfsfunktionen
# =========================================================

def esc(s):
    if s is None:
        return ""
    return str(s).replace("'", "''")


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
# Bevölkerung-Parser (Punkt 10)
# =========================================================

def parse_bevoelkerung_advanced(block_text):
    """
    Parser für Punkt 10: Bevölkerung
    """

    m = re.search(r"\b10\.\s+(.*?)(?=\n\s*\d+\.|$)", block_text, re.S)
    if not m:
        return []

    text = m.group(1)

    # Jahr : Wert
    raw_entries = re.findall(
        r"(\d{3,4}(?:[-/]\d{2,4})?)\s*:\s*([^:,]+)",
        text
    )

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
# HOL-Datei → Ortsblöcke
# =========================================================

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


# =========================================================
# SQL-Generator
# =========================================================

def sql_insert_population(place_id, entry):
    return (
        "INSERT INTO place_population "
        "(place_id, year, inhabitants, notes) VALUES ("
        f"{place_id}, "
        f"{entry['year']}, "
        f"{entry['inhabitants']}, "
        f"'{esc(entry.get('notes'))}'"
        ");"
    )


# =========================================================
# Hauptfunktion
# =========================================================

def generate_population_sql(src_path, out_path, place_id_map):
    """
    place_id_map = {"AHRENSFELDE": 482, ...}
    """

    blocks = load_blocks(src_path)
    sqls = []

    for place_name, block in blocks.items():
        if place_name not in place_id_map:
            continue

        place_id = place_id_map[place_name]
        entries = parse_bevoelkerung_advanced(block)

        for e in entries:
            sqls.append(sql_insert_population(place_id, e))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sqls))

    print(f"FERTIG: {len(sqls)} Bevölkerungseinträge → {out_path}")


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    generate_population_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\population_import.sql",
        place_id_map={
            "AHRENSFELDE": 482,
            # weitere Orte hier ergänzen
        }
    )

# --- End: generate_place_pop.py ---

