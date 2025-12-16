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
# EXTRACTORS
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

# 4. Quelle
def extract_first_mention_source(block: str):
    m = re.search(r"\b4\.[^\(]*\(([^)]+)\)", block)
    return m.group(1).strip() if m else None

# Lagehinweis (2. Zeile)
def extract_lage_hinweis(block: str):
    lines = block.strip().splitlines()
    if len(lines) >= 2:
        return lines[1].strip()
    return None

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
    }

# -------------------------------------------------------------------
# SQL Generator
# -------------------------------------------------------------------

def sql_insert_place(place_id, place_name, block):
    d = parse_place(block)

    return f"""
INSERT INTO landeskunde.places
(
    place_id,
    name,
    type,
    parent_id,
    settlement_type,
    first_mention_year,
    first_mention_source,
    description,
    lage_hinweis
)
VALUES (
    {place_id},
    {esc(place_name)},
    {esc(d['type'])},
    NULL,
    {esc(d['settlement_type'])},
    {d['first_mention_year'] if d['first_mention_year'] else "NULL"},
    {esc(d['first_mention_source'])},
    {esc(block)},
    {esc(d['lage_hinweis'])}
);
""".strip()

# -------------------------------------------------------------------
# HOL-Datei → Ortsblöcke
# -------------------------------------------------------------------

def load_blocks(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    clean = unicodedata.normalize("NFKC", raw)
    lines = clean.split("\n")

    places = []
    for i, line in enumerate(lines):
        line = line.strip()
        # nur Zeilen mit Buchstaben, min. 3 Zeichen, nicht s.
        if re.fullmatch(r"[A-ZÄÖÜ0-9' ()\/\-]+", line) and re.search(r"[A-ZÄÖÜ]", line):
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

    print("✔ places_import.sql erzeugt:", out_path)

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

if __name__ == "__main__":
    generate_places_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\places_import.sql"
    )
