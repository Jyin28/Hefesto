"""Operadores de agua (SAGA: ASADAs, CAAR, ADI...) -> data/web/asadas.json y web/public/data/asadas.json.

Entrada: «Operadores y Fuentes (Ubicaciones).xlsx» (hojas «Operadores» y «Fuentes»; encabezados en la fila 6).
El caudal inicial de cada operador es la suma del «Último caudal registrado» (L/s) de sus fuentes. Sin ninguna
medición queda en null. Solo usa la biblioteca estándar (el .xlsx se lee con zipfile + xml).
"""
import json
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "Operadores y Fuentes (Ubicaciones).xlsx"
CANTONS = ROOT / "data" / "web" / "cantons.json"
OUT = ROOT / "data" / "web" / "asadas.json"
PUBLIC_OUT = ROOT / "web" / "public" / "data" / "asadas.json"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
HEADER_ROW = 5  # índice (0) de la fila de encabezados
# Nombres del Excel que difieren de la DTA 2026: (provincia, cantón) normalizados -> código.
ALIASES = {("san jose", "leon cortes"): "120"}
SMALL_WORDS = {"de", "del", "la", "las", "los", "y", "e", "el", "en", "a"}
TYPE_LABELS = {"ASADA": "ASADA", "ASADA EN CONSTRUCCIÓN": "ASADA en construcción", "CAAR": "CAAR",
               "ASOCIACION": "Asociación", "ASOCIACION DE DESARROLLO INDIGENA": "Asociación de Desarrollo Indígena"}


def normalize(text):
    decomposed = unicodedata.normalize("NFD", str(text or "").strip().lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def title_case(text):
    """«COLORADO DE LIBERIA, GUANACASTE» -> «Colorado de Liberia, Guanacaste» (siglas cortas se conservan)."""
    words = []
    for index, word in enumerate(str(text or "").strip().split()):
        lower = word.lower()
        if index and lower in SMALL_WORDS:
            words.append(lower)
        elif re.fullmatch(r"[A-ZÁÉÍÓÚÑ]{1,3}\.?,?", word) and word.lower() not in SMALL_WORDS and len(word) <= 3 and "." in word:
            words.append(word)
        else:
            words.append("-".join(part[:1].upper() + part[1:].lower() for part in lower.split("-")))
    return " ".join(words)


def read_sheets(path):
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            for item in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("m:si", NS):
                shared.append("".join(t.text or "" for t in item.iter("{%s}t" % NS["m"])))
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        sheets = {}
        for sheet in workbook.find("m:sheets", NS):
            target = rels[sheet.get(REL)].lstrip("/")
            target = target if target.startswith("xl/") else "xl/" + target
            rows = []
            for row in ET.fromstring(archive.read(target)).findall(".//m:sheetData/m:row", NS):
                cells = {}
                for cell in row.findall("m:c", NS):
                    value = cell.find("m:v", NS)
                    kind = cell.get("t")
                    if kind == "s" and value is not None:
                        text = shared[int(value.text)]
                    elif kind == "inlineStr":
                        text = "".join(t.text or "" for t in cell.iter("{%s}t" % NS["m"]))
                    else:
                        text = value.text if value is not None else None
                    letters = re.match(r"[A-Z]+", cell.get("r")).group(0)
                    index = 0
                    for char in letters:
                        index = index * 26 + ord(char) - 64
                    cells[index - 1] = text
                width = max(cells) + 1 if cells else 0
                rows.append([cells.get(i) for i in range(width)])
            sheets[sheet.get("name")] = rows
    return sheets


def number(value):
    try:
        result = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def build():
    sheets = read_sheets(XLSX)
    cantons = json.loads(CANTONS.read_text(encoding="utf-8"))["cantons"]
    by_name = {(normalize(info["province"]), normalize(info["name"])): code for code, info in cantons.items()}
    by_name.update(ALIASES)

    sources = defaultdict(list)
    for row in sheets["Fuentes"][HEADER_ROW + 1:]:
        if not row or not row[0]:
            continue
        row = row + [None] * (16 - len(row))
        sources[row[0]].append({"name": title_case(row[8]), "caudal": number(row[15]), "basin": title_case(row[14] or row[13])})

    operators, missing = [], []
    for row in sheets["Operadores"][HEADER_ROW + 1:]:
        if not row or not row[0]:
            continue
        row = row + [None] * (9 - len(row))
        ideo, name, region, province, canton, district, kind, area, services = row[:9]
        code = by_name.get((normalize(province), normalize(canton)))
        if code is None:
            missing.append((ideo, province, canton))
            continue
        flows = [s["caudal"] for s in sources.get(ideo, []) if s["caudal"] is not None]
        operators.append({
            "id": ideo, "name": title_case(name), "type": TYPE_LABELS.get(kind, title_case(kind)),
            "region": title_case(str(region or "").replace("REGIÓN", "").strip()),
            "province": cantons[code]["province"], "canton": cantons[code]["name"], "district": title_case(district),
            "cantonCode": code, "area": title_case(area), "services": int(number(services)) if number(services) is not None else None,
            "caudal": round(sum(flows), 2) if flows else None, "sources": sources.get(ideo, []),
        })
    if missing:
        raise SystemExit(f"Operadores sin cantón reconocido: {missing[:10]} ({len(missing)} en total)")
    operators.sort(key=lambda item: (item["province"], item["canton"], item["district"], item["name"]))
    return {
        "source": {"label": "SAGA (AyA) · Entes operadores y fuentes de abastecimiento, datos al 11 de noviembre de 2026",
                   "unit": "L/s", "note": "Caudal inicial = suma del último caudal registrado de las fuentes de cada operador."},
        "operators": operators,
    }


def main():
    data = build()
    content = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    for target in (OUT, PUBLIC_OUT):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    ops = data["operators"]
    print(f"{len(ops)} operadores · {sum(1 for o in ops if o['caudal'] is not None)} con caudal inicial · "
          f"{len(content) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
