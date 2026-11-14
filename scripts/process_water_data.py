import pandas as pd
from pathlib import Path

print("Procesando datos de operadores, fuentes y agua...")
Path("data/processed").mkdir(parents=True, exist_ok=True)

# 1. Leer operadores desde el Excel de SAGA
op_file = "Operadores y Fuentes (Ubicaciones).xlsx"
if Path(op_file).exists():
    df_op = pd.read_excel(op_file, sheet_name="Operadores", skiprows=5)
    print(f"Operadores cargados: {len(df_op)} registros.")
    
    # Seleccionamos y renombramos columnas clave
    # Columnas originales: IDEO, Nombre del operador, Región, Provincia, Cantón, Distrito, Tipo de administración, Ubicación geográfica, Servicios abastecidos, Norte CRTM05, Este CRTM05
    cols_map = {
        "IDEO": "ideo",
        "Nombre del operador": "operator_name",
        "Región": "region",
        "Provincia": "province",
        "Cantón": "canton",
        "Distrito": "district",
        "Tipo de administración": "admin_type",
        "Ubicación geográfica": "geo_location",
        "Servicios abastecidos": "services_supplied",
        "Norte CRTM05": "crtm05_norte",
        "Este CRTM05": "crtm05_este"
    }
    df_op = df_op.rename(columns=cols_map)
    
    # Guardamos como CSV normalizado para el equipo
    out_csv = "data/processed/water_coverage.csv"
    df_op.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"  -> Guardado {out_csv}")
else:
    print(f"Aviso: No se encontro {op_file} en la raiz.")

# 2. Guardar resumen de fuentes de abastecimiento
if Path(op_file).exists():
    df_src = pd.read_excel(op_file, sheet_name="Fuentes", skiprows=5)
    print(f"Fuentes de abastecimiento cargadas: {len(df_src)} registros.")
    out_src_csv = "data/processed/water_distribution.csv"
    df_src.to_csv(out_src_csv, index=False, encoding="utf-8")
    print(f"  -> Guardado {out_src_csv}")

print("¡Proceso de datos hídricos completado con éxito!")
