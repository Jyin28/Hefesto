import json
import urllib.request
import urllib.error
from pathlib import Path

def fetch(url, tag):
    print(f"\n=== Probando {tag} ===")
    req = urllib.request.Request(url, headers={"User-Agent": "Hefesto-SpaceApps/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            Path(f"data/raw/{tag}.json").write_bytes(raw)
            data = json.loads(raw.decode("utf-8"))
            print("OK 200! Header:", json.dumps(data.get("header", {}), indent=2))
            print("Parameters:", json.dumps(data.get("parameters", {}), indent=2))
            feats = data.get("features", [])
            print(f"Celdas devueltas: {len(feats)}")
            for i, f in enumerate(feats):
                c = f.get("geometry", {}).get("coordinates", [])
                p = f.get("properties", {}).get("parameter", {}).get("PRECTOTCORR", {})
                ks = sorted(p.keys())
                print(f"  Celda {i+1}: coords={c} | meses={ks[:3]}..{ks[-2:]} | muestra={ {k: p[k] for k in ks[:2]} }")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body}")

# 1. Ver por que fallo la caja exacta de CR_PN
url_exact = (
    "https://power.larc.nasa.gov/api/temporal/monthly/regional"
    "?parameters=PRECTOTCORR&community=AG"
    "&longitude-min=-86.0&longitude-max=-85.0"
    "&latitude-min=9.75&latitude-max=11.25"
    "&start=2024&end=2024&format=JSON"
)
fetch(url_exact, "test_exact")

# 2. Probar caja minima 2x2 grados (requisito comun de /regional en NASA POWER)
url_2x2 = (
    "https://power.larc.nasa.gov/api/temporal/monthly/regional"
    "?parameters=PRECTOTCORR&community=AG"
    "&longitude-min=-86.5&longitude-max=-84.5"
    "&latitude-min=9.5&latitude-max=11.5"
    "&start=2024&end=2024&format=JSON"
)
fetch(url_2x2, "test_2x2")
