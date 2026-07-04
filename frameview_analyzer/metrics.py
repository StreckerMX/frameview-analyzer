"""Catálogo de métricas FrameView y descubrimiento dinámico de columnas."""

from __future__ import annotations

import re
from dataclasses import dataclass

from frameview_analyzer.csv_loader import LoadedCsv, get_numeric, is_numeric_column

TIME_COLUMN_KEYS = ["TimeInSeconds", "Timestamp (Elapsed time in seconds)"]


@dataclass(frozen=True)
class MetricDef:
    metric_id: str
    label: str
    unit: str
    category: str
    column_keys: tuple[str, ...]
    higher_is_better: bool | None = None
    computed: bool = False

    def resolve_column(self, headers: list[str]) -> str | None:
        header_set = set(headers)
        for key in self.column_keys:
            if key in header_set:
                return key
        return None


CORE_METRICS: list[MetricDef] = [
    MetricDef("fps", "FPS (calculado)", "FPS", "Rendimiento", (), higher_is_better=True, computed=True),
    MetricDef("frametime", "Frametime", "ms", "Rendimiento", ("MsBetweenPresents", "MsBetweenDisplayChange"), higher_is_better=False),
    MetricDef("latency", "Latencia PC", "ms", "Latencia", ("MsPCLatency", "Average PC Latency(MSec)", "AvgPCLatency (ms)"), higher_is_better=False),
    MetricDef("fg_multiplier", "Frame Gen Multiplier", "x", "Rendimiento", ("Frame Gen Multiplier",), higher_is_better=None),
    MetricDef("render_present_latency", "Render Present Latency", "ms", "Latencia", ("MsRenderPresentLatency", "RenderPresentLatency (ms)"), higher_is_better=False),
    MetricDef("until_displayed", "Ms Until Displayed", "ms", "Latencia", ("MsUntilDisplayed",), higher_is_better=False),
    MetricDef("in_present_api", "Ms In Present API", "ms", "Latencia", ("MsInPresentAPI",), higher_is_better=False),
    MetricDef("flip_delay", "Ms Flip Delay", "ms", "Latencia", ("MsFlipDelay",), higher_is_better=False),
    MetricDef("simulation_start", "Ms Between Simulation Start", "ms", "Rendimiento", ("MsBetweenSimulationStart",), higher_is_better=False),
    MetricDef("display_change", "Ms Between Display Change", "ms", "Rendimiento", ("MsBetweenDisplayChange",), higher_is_better=False),
    MetricDef("render_queue_depth", "Render Queue Depth", "", "Rendimiento", ("Render Queue Depth",), higher_is_better=None),
    MetricDef("dropped", "Frames Dropped", "", "Rendimiento", ("Dropped",), higher_is_better=False),
    MetricDef("gpu0_util", "GPU0 Utilización", "%", "GPU", ("GPU0Util(%)", "GPU0 Util%", "GPU Utilization(%)"), higher_is_better=True),
    MetricDef("gpu0_clk", "GPU0 Clock", "MHz", "GPU", ("GPU0Clk(MHz)",), higher_is_better=None),
    MetricDef("gpu0_mem_clk", "GPU0 Mem Clock", "MHz", "GPU", ("GPU0MemClk(MHz)",), higher_is_better=None),
    MetricDef("gpu0_temp", "GPU0 Temperatura", "°C", "GPU", ("GPU0Temp(C)", "GPU0 Temp (C)", "GPU Temperature(Degrees celsius)"), higher_is_better=False),
    MetricDef("gpu1_util", "GPU1 Utilización", "%", "GPU", ("GPU1Util(%)", "GPU1 Util%", "GPU1 Utilization(%)"), higher_is_better=True),
    MetricDef("gpu1_clk", "GPU1 Clock", "MHz", "GPU", ("GPU1Clk(MHz)",), higher_is_better=None),
    MetricDef("gpu1_mem_clk", "GPU1 Mem Clock", "MHz", "GPU", ("GPU1MemClk(MHz)",), higher_is_better=None),
    MetricDef("gpu1_temp", "GPU1 Temperatura", "°C", "GPU", ("GPU1Temp(C)", "GPU1 Temp (C)", "GPU1 Temperature(Degrees celsius)"), higher_is_better=False),
    MetricDef("nv_power", "NV GPU Power", "W", "Energía", ("NV Pwr(W) (API)", "GPU NV Power (Watts) (API)"), higher_is_better=False),
    MetricDef("gpu_only_power", "GPU Only Power", "W", "Energía", ("GPUOnlyPwr(W) (API)",), higher_is_better=False),
    MetricDef("pcat_power", "PCAT Power Total", "W", "Energía", ("PCAT Power Total(W)", "PCAT Power (Watts)"), higher_is_better=False),
    MetricDef("perf_w_api", "Perf/W (API)", "F/J", "Energía", ("Perf/W Total(F/J) (API)", "Perf/W (F/J) (PCAT)"), higher_is_better=True),
    MetricDef("cpu_util", "CPU Utilización", "%", "CPU", ("CPUUtil(%)", "CPU Util %", "CPU Utilization(%)"), higher_is_better=None),
    MetricDef("cpu_clk", "CPU Clock", "MHz", "CPU", ("CPUClk(MHz)",), higher_is_better=None),
    MetricDef("cpu_temp", "CPU Temperatura", "°C", "CPU", ("CPU Package Temp(C)", "CPU Temp (C)"), higher_is_better=False),
    MetricDef("cpu_power", "CPU Package Power", "W", "CPU", ("CPU Package Power(W)", "CPU Package Power(Watts)"), higher_is_better=False),
    MetricDef("battery_drain", "Battery Drain Rate", "W", "Energía", ("Battery Drain Rate(W)",), higher_is_better=False),
]

SKIP_COLUMNS = {
    "Application",
    "GPU",
    "CPU",
    "Resolution",
    "Runtime",
    "AllowsTearing",
    "ProcessID",
    "SwapChainAddress",
    "SyncInterval",
    "PresentFlags",
    "PresentMode",
    "FlipToken",
    "TimeStamp",
    "Log Name",
    "OS",
    "GPU Base Driver",
    "GPU Driver Package",
    "System RAM",
    "Motherboard",
    "GPU0",
    "GPU1",
}

CORE_BY_ID = {m.metric_id: m for m in CORE_METRICS}


def _guess_unit(column: str) -> str:
    if re.search(r"\(%\)|Util%", column, re.IGNORECASE):
        return "%"
    if re.search(r"\(MHz\)|Clk", column, re.IGNORECASE):
        return "MHz"
    if re.search(r"Temp|\(C\)|celsius", column, re.IGNORECASE):
        return "°C"
    if re.search(r"\(W\)|Power|Watts|Pwr", column, re.IGNORECASE):
        return "W"
    if re.search(r"\(ms\)|^Ms", column):
        return "ms"
    if re.search(r"F/J", column):
        return "F/J"
    if re.search(r"Wh", column):
        return "Wh"
    return ""


def _guess_category(column: str) -> str:
    upper = column.upper()
    if "CPU" in upper:
        return "CPU"
    if "GPU" in upper or "NV" in upper or "PCAT" in upper or "PERF/W" in upper:
        return "GPU" if "PWR" not in upper and "POWER" not in upper and "PERF" not in upper else "Energía"
    if "BATTERY" in upper:
        return "Energía"
    if "LATENCY" in upper or column.startswith("Ms"):
        return "Latencia"
    return "Otros"


def _column_metric_id(column: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", column).strip("_").lower()
    return f"col_{slug}"[:64]


def build_metric_catalog(loaded: LoadedCsv) -> list[MetricDef]:
    if loaded.kind != "log":
        return []

    headers = loaded.headers
    catalog: list[MetricDef] = []
    used_columns: set[str] = set()

    for metric in CORE_METRICS:
        if metric.computed:
            catalog.append(metric)
            continue
        column = metric.resolve_column(headers)
        if column and is_numeric_column(loaded.rows, column):
            catalog.append(metric)
            used_columns.add(column)

    for column in headers:
        if column in SKIP_COLUMNS or column in TIME_COLUMN_KEYS or column in used_columns:
            continue
        if not is_numeric_column(loaded.rows, column):
            continue
        catalog.append(
            MetricDef(
                metric_id=_column_metric_id(column),
                label=column,
                unit=_guess_unit(column),
                category=_guess_category(column),
                column_keys=(column,),
            )
        )

    return catalog


def get_metric_value(row: dict[str, str], metric: MetricDef, headers: list[str]) -> float | None:
    if metric.metric_id == "fps":
        ft = get_metric_value(row, CORE_BY_ID["frametime"], headers)
        return (1000.0 / ft) if ft and ft > 0 else None
    if metric.metric_id == "frametime":
        ft = get_numeric(row, list(metric.column_keys))
        if ft is not None and ft > 0:
            return ft
        fps = get_numeric(row, ["FPS"])
        return (1000.0 / fps) if fps and fps > 0 else None
    return get_numeric(row, list(metric.column_keys))


def metric_unit(metric: MetricDef) -> str:
    return metric.unit


def metric_stat_fields(metric_id: str) -> list[tuple[str, str]]:
    if metric_id in {"frametime", "latency", "render_present_latency", "until_displayed", "in_present_api", "flip_delay"}:
        return [("avg", "Prom"), ("p1", "1% High"), ("p01", "0.1% High"), ("max", "Pico"), ("min", "Mín")]
    if metric_id == "fg_multiplier":
        return [("avg", "Prom"), ("min", "Mín"), ("max", "Máx")]
    if metric_id in {"gpu0_util", "gpu1_util", "cpu_util", "gpu0_temp", "gpu1_temp", "cpu_temp"}:
        return [("avg", "Prom"), ("max", "Pico"), ("min", "Mín")]
    return [("avg", "Prom"), ("p1", "1% Low"), ("p01", "0.1% Low"), ("max", "Max"), ("min", "Min")]