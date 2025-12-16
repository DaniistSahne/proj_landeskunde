import re
import unicodedata

# ============================
# 1) NORMALISIERUNG
# ============================
def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().upper()

# ============================
# 2) BLOCK-SCHNEIDER
# ============================
def load_blocks(path):
    """
    Trennt die Datei in Blöcke anhand von Großbuchstaben-Zeilen.
    Jede solche Zeile gilt als neuer Ort.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    clean = unicodedata.normalize("NFKC", raw)
    lines = clean.split("\n")

    places = []
    for i, line in enumerate(lines):
        line_clean = line.strip()
        # Nur Zeilen, die mit Buchstaben starten, zählen als Ort
        if re.fullmatch(r"[A-ZÄÖÜ][A-ZÄÖÜ0-9' ()\/\-]*", line_clean):
            places.append((line_clean, i))

    blocks = {}
    for idx, (place_name, start) in enumerate(places):
        end = places[idx + 1][1] if idx + 1 < len(places) else len(lines)
        block = "\n".join(lines[start:end])
        blocks[place_name] = block

    return blocks

# ============================
# 3) ALIAS-PARSER
# ============================
def parse_aliases(block_text):
    """
    Parst den 4. Punkt (falls vorhanden) und extrahiert die Aliase.
    """
    p4 = re.search(r"4\.\s*(.+?)(?=\n\d+\.)", block_text, flags=re.S)
    if not p4:
        return []  # Kein 4. Punkt → keine Aliase

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

        for alias in names_str.split(","):
            aliases.append({
                "alias": alias.strip(),
                "year_from": year,
                "year_to": None,
                "source": source
            })

    return aliases

# ============================
# 4) SQL-GENERATOR
# ============================
def esc(s):
    return s.replace("'", "''") if s else s

def sql_insert_temp(place_name, a):
    alias_val = f"'{esc(a['alias'])}'" if a['alias'] else f"'{esc(place_name)}'"
    year_from_val = a['year_from'] if a['year_from'] else "NULL"
    year_to_val = a['year_to'] if a['year_to'] else "NULL"
    source_val = f"'{esc(a['source'])}'" if a['source'] else "NULL"

    return (
        "INSERT INTO place_alias_temp "
        "(place_name, alias, year_from, year_to, source) VALUES ("
        f"'{esc(place_name)}', {alias_val}, {year_from_val}, {year_to_val}, {source_val});"
    )


# ============================
# 5) MAIN
# ============================
def generate_alias_temp_sql(src_path, out_path):
    blocks = load_blocks(src_path)
    sql_lines = []

    for place_name, block in blocks.items():
        normalized_name = norm_name(place_name)
        aliases = parse_aliases(block)

        if not aliases:
            # Kein 4. Punkt → Eintrag mit alias=NULL
            sql_lines.append(sql_insert_temp(normalized_name, {"alias": None, "year_from": None, "year_to": None, "source": None}))
            print(f"ℹ️ Kein 4. Punkt / Alias=NULL für Ort: {place_name}")
        else:
            for a in aliases:
                sql_lines.append(sql_insert_temp(normalized_name, a))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_lines))

    print("✅ FERTIG: SQL für place_alias_temp geschrieben:", out_path)

# ============================
# 6) START
# ============================
if __name__ == "__main__":
    generate_alias_temp_sql(
        src_path=r"C:\Users\daniil\Desktop\proj_landeskunde\data\hol\txt\HOL_BB_6_normalized.txt",
        out_path=r"C:\Users\daniil\Desktop\proj_landeskunde\src\parser\aliases_temp.sql"
    )
