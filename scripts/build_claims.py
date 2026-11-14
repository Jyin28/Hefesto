"""Regenera las afirmaciones calculadas de docs/claims.csv desde el servicio real (result_id incluido).

Uso: python scripts/build_claims.py   (conserva CLM-01..CLM-05 y reescribe CLM-06 en adelante)
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import service  # noqa: E402
from src.contracts import QueryParams  # noqa: E402

PATH = ROOT / "docs" / "claims.csv"


def main() -> None:
    with PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    header, kept = rows[0], [r for r in rows[1:] if int(r[0].split("-")[1]) <= 5]
    new, n = [], 6
    for variable, preset in (("T2M", "CR_HEAT"), ("PRECTOTCORR", "CR_RAIN")):
        card = service.build_evidence_card(QueryParams(variable, ("CR_PN", "CR_CAR"), 1981, 2024, preset))
        rid = card["result_id"]
        res = {r["region_id"]: r for r in card["results"]}
        unit = res["CR_PN"]["slope_unit"]

        def pair(key, nd=6):
            return " y ".join(f"{res[r][key]:.{nd}g}" for r in ("CR_PN", "CR_CAR"))

        ci = " y ".join(f"[{res[r]['ci_low']:.4g}, {res[r]['ci_high']:.4g}]" for r in ("CR_PN", "CR_CAR"))
        new += [
            [f"CLM-{n:02d}", f"Pendientes OLS por década, Pacífico Norte y Caribe: {pair('slope_per_decade')} {unit}. NASA POWER, 1981–2024.", rid, "Emanuel", "CALCULADO_VERIFICADO_STATSMODELS"],
            [f"CLM-{n + 1:02d}", f"IC individuales HAC (L=3) al 95 % en {unit}: {ci}. NASA POWER, 1981–2024.", rid, "Emanuel", "CALCULADO_VERIFICADO_STATSMODELS"],
            [f"CLM-{n + 2:02d}", f"p ajustado BY (familia regional de 4 pruebas), Pacífico Norte y Caribe: {pair('p_adjusted', 4)}. NASA POWER, 1981–2024.", rid, "Emanuel", "CALCULADO_VERIFICADO_STATSMODELS"],
        ]
        n += 3
    new.append([f"CLM-{n:02d}", "La lluvia de reanálisis no está validada contra estaciones: las pendientes de PRECTOTCORR (cientos de mm/año por década) son un patrón del producto y NO deben presentarse como lluvia observada. NASA POWER documenta que los datos recientes pueden provenir de GEOS-IT sin normalización por pluviómetros.", "S2;" + rid, "Emanuel", "ADVERTENCIA_OBLIGATORIA"])
    with PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(kept + new)
    for row in new:
        print(row[0], row[1][:110], row[2])


if __name__ == "__main__":
    main()
