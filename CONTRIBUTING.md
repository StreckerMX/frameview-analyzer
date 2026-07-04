# Contribuir a FrameView Analyzer

¡Gracias por tu interés en mejorar el proyecto!

## Cómo reportar un bug

1. Verifica que usas Python 3.10+ y la última versión del repositorio.
2. Comprueba que el archivo es un `*_Log.csv` válido de FrameView.
3. Abre un [issue en GitHub](https://github.com/StreckerMX/frameview-analyzer/issues) con:
   - Versión de Windows y Python
   - Nombre del juego/aplicación y GPU
   - Pasos para reproducir
   - Mensaje de error (si aplica)
   - Fragmento del encabezado CSV (primera línea)

**No adjuntes CSV completos** si contienen datos personales; basta con las columnas y 2–3 filas de ejemplo.

## Cómo proponer mejoras

- Describe el caso de uso (ej. "comparar 5 sesiones a la vez").
- Si es una métrica nueva, indica el nombre exacto de la columna FrameView.

## Desarrollo local

```powershell
git clone https://github.com/StreckerMX/frameview-analyzer.git
cd frameview-analyzer
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r FrameViewAnalyzer.Requirements.txt
python Start-FrameViewAnalyzer.py
```

### Estructura

- `frameview_analyzer/csv_loader.py` — parsing CSV
- `frameview_analyzer/metrics.py` — definiciones de métricas
- `frameview_analyzer/analytics.py` — lógica de bins y tramo activo
- `frameview_analyzer/gui_app.py` — interfaz

### Estilo de código

- Python 3.10+ con type hints
- Nombres y UI en español (público objetivo hispanohablante)
- Cambios mínimos y enfocados; sin refactors no relacionados

## Pull requests

1. Crea una rama desde `main`
2. Un commit por cambio lógico
3. Prueba con al menos un CSV real de FrameView
4. Actualiza `CHANGELOG.md` si el cambio es visible para el usuario

## Licencia

Al contribuir, aceptas que tu código se publique bajo la [licencia MIT](LICENSE).