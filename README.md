# FrameView Analyzer

Aplicación en Python para analizar los CSV exportados por **NVIDIA FrameView** (PresentMon). Visualiza gráficos temporales de FPS, latencia, uso de GPU/CPU, temperatura, energía y **todas las columnas numéricas** del log.

## Características

- Carga archivos `*_Log.csv` de FrameView
- Gráfico temporal por métrica con filtro de tramo activo (umbral GPU)
- Estadísticas: promedio, 1% low/high, 0.1% low/high, min y max
- Comparación de dos sesiones en el mismo gráfico
- Selector con todas las métricas exportadas (incluye núcleos CPU, potencia, clocks, etc.)
- Exportar gráfico a PNG

## Requisitos

- Windows 10/11
- Python 3.10+
- Logs generados por [NVIDIA FrameView](https://www.nvidia.com/en-us/geforce/technologies/frameview/)

## Uso rápido

```powershell
cd frameview-analyzer
python -m pip install -r FrameViewAnalyzer.Requirements.txt
python Start-FrameViewAnalyzer.py
```

O con PowerShell:

```powershell
.\Start-FrameViewAnalyzer.ps1
```

## Instalación remota

```powershell
irm https://raw.githubusercontent.com/StreckerMX/frameview-analyzer/main/Install-Remote.ps1 | iex
```

Se instala en `%LOCALAPPDATA%\FrameViewAnalyzer`.

## Archivos CSV compatibles

| Tipo | Archivo | Uso |
|------|---------|-----|
| Log | `FrameView_*_Log.csv` | Gráficos temporales (recomendado) |
| Summary | `FrameView_Summary.csv` | Resumen por sesión (no soporta gráfico temporal aún) |

Los logs suelen guardarse en `Documents\FrameView\`.

## Métricas principales

- **FPS** — calculado desde `MsBetweenPresents`
- **Frametime** — milisegundos entre frames
- **Latencia PC** — `MsPCLatency`
- **Frame Gen Multiplier** — multiplicador MFG/FG
- **GPU/CPU** — utilización, clocks, temperatura, potencia
- **Columnas adicionales** — detectadas automáticamente del CSV

## Filtro de tramo activo

Para ignorar menús y pantallas de carga, la app detecta el tramo donde la GPU supera un umbral. Puedes usar umbral automático o fijarlo manualmente, y recortar segundos en los bordes.

## Licencia

Uso personal. NVIDIA FrameView es propiedad de NVIDIA Corporation.