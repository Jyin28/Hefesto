"""Normalize a WGS 84 canton GeoJSON obtained from the team's mapping source."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
IGN_LAYER = "https://services8.arcgis.com/gEjMfQjIBmRHMGao/arcgis/rest/services/Cantones_de_Costa_Rica/FeatureServer/0"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, nargs="?")
    parser.add_argument("--ign", action="store_true", help="Descarga la capa cantonal publicada del IGN")
    parser.add_argument("--code-field", default="code")
    parser.add_argument("--name-field", default="name")
    parser.add_argument("--province-field", default="province")
    parser.add_argument("--output", type=Path, default=ROOT / "web" / "public" / "data" / "cantones.geojson")
    args = parser.parse_args()
    if args.ign == bool(args.file):
        parser.error("Indique un archivo o --ign.")
    if args.ign:
        options = urlencode({"where": "1=1", "outFields": "cod_canton,canton,provincia",
                             "outSR": 4326, "maxAllowableOffset": 0.001, "f": "geojson"})
        try:
            with urlopen(f"{IGN_LAYER}/query?{options}", timeout=45) as response:
                source = json.load(response)
        except (URLError, TimeoutError) as error:
            parser.error(f"No fue posible descargar la capa cantonal: {error}")
        args.code_field, args.name_field, args.province_field = "cod_canton", "canton", "provincia"
    else:
        source = json.loads(args.file.read_text(encoding="utf-8-sig"))
    if source.get("type") != "FeatureCollection" or not source.get("features"):
        parser.error("Se necesita un GeoJSON FeatureCollection con polígonos cantonales.")

    features = []
    codes = set()
    for feature in source["features"]:
        fields = feature["properties"]
        raw_code = fields.get(args.code_field, "")
        if isinstance(raw_code, float) and raw_code.is_integer():
            raw_code = int(raw_code)
        code = str(raw_code).strip()
        name = str(fields.get(args.name_field) or "").strip()
        province = str(fields.get(args.province_field) or "").strip()
        geometry = feature["geometry"]
        if len(code) != 3 or not code.isascii() or not code.isdecimal() or not name or code in codes:
            parser.error(f"Código duplicado o campos de identificación inválidos: {code!r}, {name!r}.")
        if not geometry or geometry["type"] not in {"Polygon", "MultiPolygon"}:
            parser.error(f"El cantón {code} debe ser Polygon o MultiPolygon.")
        polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        if not polygons or any(not polygon for polygon in polygons):
            parser.error(f"Geometría vacía en el cantón {code}.")
        for polygon in polygons:
            for ring in polygon:
                if len(ring) < 4 or ring[0] != ring[-1] or any(
                    not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90) for point in ring
                ):
                    parser.error(f"Revisá los anillos y la proyección EPSG:4326 para el cantón {code}.")
        codes.add(code)
        features.append({"type": "Feature", "id": code, "geometry": geometry,
                         "properties": {"code": code, "name": name, "province": province}})

    reference = json.loads((ROOT / "data" / "web" / "cantons.json").read_text(encoding="utf-8"))
    expected_codes = set(reference["cantons"])
    if args.ign and codes != expected_codes:
        parser.error(f"La capa no coincide con los 84 códigos de la DTA 2026. "
                     f"Faltan {sorted(expected_codes - codes)}. Sobran {sorted(codes - expected_codes)}.")

    target = args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                                 ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(codes)} cantones guardados en {target}")


if __name__ == "__main__":
    main()
