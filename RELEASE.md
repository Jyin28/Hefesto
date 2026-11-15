# RELEASE — checklist MVP (rama `MVP`)

## Antes de entregar
- [ ] `scripts\verify_data.py` → "Datos verificados".
- [ ] `pytest -q` en verde.
- [ ] `.\package.ps1` genera `dist\hefesto-mvp.zip` (+ `.sha256`).
- [ ] Descomprimir en una segunda computadora, `.\run.ps1`, abrir http://localhost:8501 **sin internet** y completar ambos recorridos.
- [ ] Medir inicio (< 60 s) y consulta cacheada (< 3 s). *(Metas del plan; no son mediciones hechas aún en segunda máquina.)*
- [ ] Las cifras del pitch coinciden con `docs/claims.csv` (result_id) y con la pantalla/descarga.
- [ ] Ninguna cifra sintética en el release (el banner de mock solo aparece con `HEFESTO_USE_MOCK=1`).

## Pendientes humanos (no automatizables)
- [ ] Confirmar el formato ejecutable aceptado por el jurado [verificar].
- [ ] Revisión independiente de ciencia (Jacky/Samuel) y de PR por otra persona.
- [ ] Validar la lluvia contra estaciones locales (IMN) antes de afirmar magnitudes de lluvia observada.
- [ ] Verificar boletines IMN del episodio 1997–98 y su período neutral de contraste (hoy: no verificado).
- [ ] Grabar video 90–120 s desde la versión final; subir y confirmar recepción; enlaces desde otra sesión.
- [ ] Firmas del acuerdo de equipo.

## Contenido
Código MIT (`LICENSE`); datos NASA POWER y dependencias con sus términos (`THIRD_PARTY.md`); uso de IA en `AI_USAGE.md`.
