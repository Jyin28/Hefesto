# Hefesto
NASA Space Apps Hackathon

El alcance del sitio web y el orden de implementación están en el [plan del MVP Detective Tico](docs/PLAN-HEFESTO.md).

El [estado del equipo y la validación](docs/validation.md) incluyen qué se integró a GitHub, las cifras reproducibles y los pendientes para la demo. La app principal usa el paquete NASA POWER del repositorio. Para abrir el asistente de prueba de Kevin, definí `$env:HEFESTO_USE_MOCK = "1"` antes de arrancar Streamlit. La [versión React y su API](web/README.md) tienen instrucciones propias.

## Entorno

Usá un Python compatible con las versiones de `requirements.txt`. Cada integrante crea su propio `.venv`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m streamlit run app.py
.\.venv\Scripts\python.exe -m pytest -q
```
