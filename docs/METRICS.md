# Referencia de métricas FrameView

Guía de las métricas que **FrameView Analyzer** puede graficar a partir de archivos `*_Log.csv`.

---

## Cómo se calculan los gráficos

1. Cada fila del CSV = un frame presentado.
2. Los valores se agrupan en **bins de 1 segundo** (`TimeInSeconds`).
3. Solo se incluyen bins dentro del **tramo activo** (GPU ≥ umbral).
4. **FPS** no usa el promedio simple de frametimes: se calcula como `1000 × frames / suma_ms` por bin.

---

## Rendimiento

| ID | Etiqueta | Columna(s) | Unidad | Más alto = mejor |
|----|----------|------------|--------|------------------|
| `fps` | FPS (calculado) | Derivado de `MsBetweenPresents` | FPS | Sí |
| `frametime` | Frametime | `MsBetweenPresents`, `MsBetweenDisplayChange` | ms | No |
| `fg_multiplier` | Frame Gen Multiplier | `Frame Gen Multiplier` | x | Depende |
| `simulation_start` | Ms Between Simulation Start | `MsBetweenSimulationStart` | ms | No |
| `display_change` | Ms Between Display Change | `MsBetweenDisplayChange` | ms | No |
| `render_queue_depth` | Render Queue Depth | `Render Queue Depth` | — | No |
| `dropped` | Frames Dropped | `Dropped` | — | No |

### Frame Gen Multiplier

- **1** = rendering nativo, sin interpolación.
- **2, 3, 4…** = Multi-Frame Generation (MFG) activo.
- Caídas a **0** o valores inestables indican que MFG se desactivó temporalmente.

---

## Latencia

| ID | Etiqueta | Columna(s) | Unidad | Más bajo = mejor |
|----|----------|------------|--------|------------------|
| `latency` | Latencia PC | `MsPCLatency` | ms | Sí |
| `render_present_latency` | Render Present Latency | `MsRenderPresentLatency` | ms | Sí |
| `until_displayed` | Ms Until Displayed | `MsUntilDisplayed` | ms | Sí |
| `in_present_api` | Ms In Present API | `MsInPresentAPI` | ms | Sí |
| `flip_delay` | Ms Flip Delay | `MsFlipDelay` | ms | Sí |

`MsPCLatency` es la métrica principal de **latencia de sistema** mostrada en FrameView.

---

## GPU

| ID | Etiqueta | Columna(s) | Unidad |
|----|----------|------------|--------|
| `gpu0_util` | GPU0 Utilización | `GPU0Util(%)` | % |
| `gpu0_clk` | GPU0 Clock | `GPU0Clk(MHz)` | MHz |
| `gpu0_mem_clk` | GPU0 Mem Clock | `GPU0MemClk(MHz)` | MHz |
| `gpu0_temp` | GPU0 Temperatura | `GPU0Temp(C)` | °C |
| `gpu1_util` | GPU1 Utilización | `GPU1Util(%)` | % |
| `gpu1_clk` | GPU1 Clock | `GPU1Clk(MHz)` | MHz |
| `gpu1_mem_clk` | GPU1 Mem Clock | `GPU1MemClk(MHz)` | MHz |
| `gpu1_temp` | GPU1 Temperatura | `GPU1Temp(C)` | °C |

En sistemas con una sola GPU, las columnas `GPU1*` suelen ser `NA`.

---

## CPU

| ID | Etiqueta | Columna(s) | Unidad |
|----|----------|------------|--------|
| `cpu_util` | CPU Utilización | `CPUUtil(%)` | % |
| `cpu_clk` | CPU Clock | `CPUClk(MHz)` | MHz |
| `cpu_temp` | CPU Temperatura | `CPU Package Temp(C)` | °C |
| `cpu_power` | CPU Package Power | `CPU Package Power(W)` | W |

### Núcleos individuales

FrameView exporta hasta 64 columnas:

```
CPUCoreUtil%[ 0], CPUCoreUtil%[ 1], … CPUCoreUtil%[63]
```

Se detectan automáticamente y aparecen en el selector bajo categoría **CPU**.

---

## Energía

| ID | Etiqueta | Columna(s) | Unidad |
|----|----------|------------|--------|
| `nv_power` | NV GPU Power | `NV Pwr(W) (API)` | W |
| `gpu_only_power` | GPU Only Power | `GPUOnlyPwr(W) (API)` | W |
| `pcat_power` | PCAT Power Total | `PCAT Power Total(W)` | W |
| `perf_w_api` | Perf/W (API) | `Perf/W Total(F/J) (API)` | F/J |
| `battery_drain` | Battery Drain Rate | `Battery Drain Rate(W)` | W |

Requieren hardware compatible (PCAT, sensores de potencia NVIDIA API, etc.). Si no hay sensor, el valor será `NA`.

---

## Estadísticas mostradas

| Tipo de métrica | Prom | 1% | 0.1% | Min | Max |
|-----------------|------|-----|------|-----|-----|
| FPS, GPU util, potencia | Prom | 1% **Low** | 0.1% **Low** | Min | Max |
| Frametime, latencia | Prom | 1% **High** | 0.1% **High** | Mín | Pico |
| Frame Gen | Prom | — | — | Mín | Máx |

- **1% Low (FPS)**: el 1% peor de bins por segundo → métrica estándar de benchmark.
- **1% High (latencia)**: el 1% peor de latencias → picos de input lag.

---

## Columnas excluidas del gráfico

Estas columnas son metadatos de sesión, no series temporales:

- `Application`, `GPU`, `CPU`, `Resolution`, `Runtime`
- `ProcessID`, `SwapChainAddress`, `PresentMode`, `PresentFlags`
- `AllowsTearing`, `SyncInterval`, `FlipToken`

---

## Archivo Summary (`FrameView_Summary.csv`)

Contiene promedios por sesión (no frame a frame). Columnas típicas:

| Columna Summary | Equivalente en log |
|-----------------|-------------------|
| `Avg FPS` | Promedio FPS sesión |
| `1% Low` | 1% low FPS |
| `0.1% Low FPS` | 0.1% low FPS |
| `AvgPCLatency (ms)` | Latencia media |
| `GPU0 Util%` | Uso GPU medio |
| `Time (sec)` | Duración sesión |

Soporte de gráficos para Summary está planificado en una versión futura.