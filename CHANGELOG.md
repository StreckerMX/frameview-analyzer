# Changelog

Todos los cambios notables de este proyecto se documentan aquí.

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [1.0.1] - 2026-07-04

### Corregido

- Crash al abrir la app: matplotlib no aceptaba colores tipo `gray70` de CustomTkinter
- Conflicto pack/grid en la tarjeta del gráfico que impedía iniciar la interfaz

## [1.0.0] - 2026-07-04

### Añadido

- Interfaz gráfica con CustomTkinter y tema oscuro NVIDIA
- Carga de archivos `FrameView_*_Log.csv`
- Gráficos temporales con matplotlib (FPS, latencia, GPU, CPU, energía, Frame Gen)
- Descubrimiento automático de columnas numéricas (núcleos CPU, clocks, potencia, etc.)
- Filtro de tramo activo por umbral GPU (automático y manual)
- Recorte de bordes del tramo activo (0–10 s)
- Comparación de dos sesiones con panel de delta
- Estadísticas: promedio, 1% low/high, 0.1% low/high, min y max
- Exportación de gráficos a PNG
- Instalador remoto `Install-Remote.ps1` con venv y acceso directo
- Desinstalador `Uninstall-FrameViewAnalyzer.ps1`
- Documentación: README, METRICS.md, CONTRIBUTING.md

[1.0.0]: https://github.com/StreckerMX/frameview-analyzer/releases/tag/v1.0.0