"""Hidrografía de Costa Rica (HOT/OSM) -> web/public/data/waterways.geojson, ligera para el navegador.

Entrada: data/raw/hidrografia/hotosm_cri_waterways_osm_geojson.zip (OpenStreetMap, ODbL).
Conserva ríos, canales y quebradas (líneas) y cuerpos de agua (polígonos `natural=water`); descarta puntos
(cascadas, represas) y humedales. Simplifica con Douglas-Peucker y redondea a 5 decimales.
"""
import argparse
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "data" / "raw" / "hidrografia" / "hotosm_cri_waterways_osm_geojson.zip"
OUT = ROOT / "web" / "public" / "data" / "waterways.geojson"
LINE_KINDS = {"river": "river", "canal": "canal", "stream": "stream"}
TOLERANCE = 0.0003  # grados (~33 m)
MAX_MB = 5.0


def simplify(points, tolerance):
    """Douglas-Peucker iterativo (sin recursión, hay líneas con miles de vértices)."""
    if len(points) <= 2:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    tol2 = tolerance * tolerance
    while stack:
        first, last = stack.pop()
        (x1, y1), (x2, y2) = points[first], points[last]
        dx, dy = x2 - x1, y2 - y1
        length2 = dx * dx + dy * dy
        worst, index = -1.0, -1
        for i in range(first + 1, last):
            px, py = points[i]
            if length2 == 0:
                d2 = (px - x1) ** 2 + (py - y1) ** 2
            else:
                t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length2))
                d2 = (px - x1 - t * dx) ** 2 + (py - y1 - t * dy) ** 2
            if d2 > worst:
                worst, index = d2, i
        if worst > tol2:
            keep[index] = True
            stack.append((first, index))
            stack.append((index, last))
    return [p for p, k in zip(points, keep) if k]


def round_ring(points):
    return [[round(x, 5), round(y, 5)] for x, y in points]


def build(drop_unnamed_streams=False):
    with zipfile.ZipFile(ZIP) as archive:
        source = json.loads(archive.read("waterways.geojson"))
    features = []
    counts = {"river": 0, "canal": 0, "stream": 0, "water": 0}
    for feature in source["features"]:
        props, geometry = feature["properties"], feature["geometry"]
        name = props.get("name") or None
        if geometry["type"] in ("LineString", "MultiLineString"):
            kind = LINE_KINDS.get(props.get("waterway"))
            if kind is None or (drop_unnamed_streams and kind == "stream" and not name):
                continue
            parts = [geometry["coordinates"]] if geometry["type"] == "LineString" else geometry["coordinates"]
            lines = [round_ring(simplify([(x, y) for x, y, *_ in part], TOLERANCE)) for part in parts]
            lines = [line for line in lines if len(line) >= 2]
            if not lines:
                continue
            geom = {"type": "LineString", "coordinates": lines[0]} if len(lines) == 1 else {"type": "MultiLineString", "coordinates": lines}
            features.append({"type": "Feature", "properties": {"name": name, "kind": kind}, "geometry": geom})
            counts[kind] += 1
        elif geometry["type"] in ("Polygon", "MultiPolygon") and props.get("natural_class") == "water":
            polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
            out = []
            for polygon in polygons:
                rings = [round_ring(simplify([(x, y) for x, y, *_ in ring], TOLERANCE)) for ring in polygon]
                rings = [ring for ring in rings if len(ring) >= 4]
                if rings:
                    out.append(rings)
            if not out:
                continue
            geom = {"type": "Polygon", "coordinates": out[0]} if len(out) == 1 else {"type": "MultiPolygon", "coordinates": out}
            features.append({"type": "Feature", "properties": {"name": name, "kind": "water"}, "geometry": geom})
            counts["water"] += 1
    return {"type": "FeatureCollection", "features": features}, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    for drop in (False, True):
        collection, counts = build(drop_unnamed_streams=drop)
        content = json.dumps(collection, ensure_ascii=False, separators=(",", ":"))
        size = len(content.encode("utf-8")) / 1e6
        print(f"{'sin quebradas anónimas' if drop else 'completo'}: {size:.2f} MB · {counts}")
        if size <= MAX_MB:
            break
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(content, encoding="utf-8")
    print(f"Escrito {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
