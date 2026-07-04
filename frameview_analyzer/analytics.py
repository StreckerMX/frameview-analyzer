"""Análisis temporal de sesiones FrameView (ventana activa, bins, estadísticas)."""

from __future__ import annotations

from dataclasses import dataclass

from frameview_analyzer.csv_loader import LoadedCsv, get_numeric, get_row_string
from frameview_analyzer.metrics import (
    CORE_BY_ID,
    MetricDef,
    TIME_COLUMN_KEYS,
    build_metric_catalog,
    get_metric_value,
    metric_stat_fields,
)

FPS_BIN_SECONDS = 1.0
DEFAULT_GPU_THRESHOLD = 10.0
DEFAULT_TRIM_BUFFER_SECONDS = 1.0
FPS_CHART_CAP = 5000.0
MIN_FRAMES_PER_BIN = 3
AUTO_GPU_RATIO = 0.30
AUTO_GPU_MIN = 5.0
AUTO_GPU_MAX = 40.0


@dataclass
class ChartPoint:
    x: float
    y: float


@dataclass
class SessionMetadata:
    application: str
    resolution: str
    gpu: str
    cpu: str
    duration: str
    frame_count: int


@dataclass
class AnalysisOptions:
    gpu_threshold: float = DEFAULT_GPU_THRESHOLD
    trim_buffer_seconds: float = DEFAULT_TRIM_BUFFER_SECONDS
    auto_gpu_threshold: bool = True


@dataclass
class SessionAnalysis:
    loaded: LoadedCsv
    catalog: list[MetricDef]
    parsed: list[dict]
    options: AnalysisOptions
    metadata: SessionMetadata | None


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def percentile(sorted_values: list[float], p: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (len(sorted_values) - 1) * p
    lower = int(pos)
    upper = min(lower + 1, len(sorted_values) - 1)
    if lower == upper:
        return sorted_values[lower]
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (pos - lower)


def clamp_gpu_threshold(value: float) -> float:
    return max(0.0, min(100.0, value))


def normalize_trim_buffer(value: float) -> float:
    if value != value:
        return DEFAULT_TRIM_BUFFER_SECONDS
    return max(0.0, min(10.0, value))


def get_time(row: dict[str, str]) -> float | None:
    return get_numeric(row, TIME_COLUMN_KEYS)


def get_gpu_util(row: dict[str, str]) -> float | None:
    return get_numeric(row, ["GPU0Util(%)", "GPU1Util(%)", "GPU1 Utilization(%)", "GPU Utilization(%)", "GPU0 Util%"])


def get_frametime_ms(row: dict[str, str]) -> float | None:
    ft = get_numeric(row, ["MsBetweenPresents", "MsBetweenDisplayChange"])
    if ft is not None and ft > 0:
        return ft
    fps = get_numeric(row, ["FPS"])
    return (1000.0 / fps) if fps and fps > 0 else None


def build_parsed_samples(rows: list[dict[str, str]]) -> list[dict]:
    parsed: list[dict] = []
    for row in rows:
        t = get_time(row)
        if t is None:
            continue
        ft = get_frametime_ms(row)
        util = get_gpu_util(row)
        fps = (1000.0 / ft) if ft and ft > 0 else None
        parsed.append({"t": t, "ft": ft, "fps": fps, "util": util, "row": row})
    parsed.sort(key=lambda item: item["t"])
    return parsed


def compute_auto_gpu_threshold(parsed: list[dict]) -> float:
    utils = [s["util"] for s in parsed if s["util"] is not None]
    if not utils:
        return DEFAULT_GPU_THRESHOLD
    avg_util = mean(utils)
    if avg_util is None:
        return DEFAULT_GPU_THRESHOLD
    threshold = round(avg_util * AUTO_GPU_RATIO)
    return clamp_gpu_threshold(max(AUTO_GPU_MIN, min(AUTO_GPU_MAX, threshold)))


def infer_active_window(parsed: list[dict], threshold: float, trim_buffer_seconds: float) -> dict[str, float] | None:
    if not parsed:
        return None

    trim_buffer = normalize_trim_buffer(trim_buffer_seconds)
    bins: dict[int, dict] = {}
    for sample in parsed:
        index = int(sample["t"] // FPS_BIN_SECONDS)
        if index not in bins:
            bins[index] = {"start": index * FPS_BIN_SECONDS, "util_sum": 0.0, "util_count": 0}
        if sample["util"] is not None:
            bins[index]["util_sum"] += sample["util"]
            bins[index]["util_count"] += 1

    bin_array = sorted(bins.values(), key=lambda b: b["start"])
    active_bins = [
        b for b in bin_array if b["util_count"] > 0 and (b["util_sum"] / b["util_count"]) >= threshold
    ]
    if not active_bins:
        return {"start": parsed[0]["t"], "end": parsed[-1]["t"] + FPS_BIN_SECONDS}

    active_starts = sorted(b["start"] for b in active_bins)
    runs: list[dict] = []
    run_start = active_starts[0]
    run_end = active_starts[0]
    for start in active_starts[1:]:
        if start == run_end + FPS_BIN_SECONDS:
            run_end = start
        else:
            runs.append({"start": run_start, "end": run_end, "length": ((run_end - run_start) / FPS_BIN_SECONDS) + 1})
            run_start = start
            run_end = start
    runs.append({"start": run_start, "end": run_end, "length": ((run_end - run_start) / FPS_BIN_SECONDS) + 1})

    sustained = [r for r in runs if r["length"] >= 3]
    chosen = max(sustained or runs, key=lambda r: r["length"])
    chosen_start = chosen["start"]
    chosen_end = chosen["end"] + FPS_BIN_SECONDS
    max_end = parsed[-1]["t"] + FPS_BIN_SECONDS

    if trim_buffer > 0 and chosen_end - chosen_start > trim_buffer * 2 + FPS_BIN_SECONDS:
        start = max(parsed[0]["t"], chosen_start + trim_buffer)
        end = min(max_end, chosen_end - trim_buffer)
    else:
        start = max(parsed[0]["t"], chosen_start)
        end = min(max_end, chosen_end)
    return {"start": start, "end": end}


def format_duration(seconds: float) -> str:
    if seconds != seconds or seconds <= 0:
        return "--"
    total = int(round(seconds))
    mins, secs = divmod(total, 60)
    if mins == 0:
        return f"{secs} s"
    return f"{mins} min {secs} s"


def extract_metadata(loaded: LoadedCsv, parsed: list[dict], threshold: float, trim_buffer: float) -> SessionMetadata | None:
    if not loaded.rows or not parsed:
        return None
    row = loaded.rows[0]
    active = infer_active_window(parsed, threshold, trim_buffer)
    duration_sec = max(0.0, active["end"] - active["start"]) if active else 0.0
    return SessionMetadata(
        application=get_row_string(row, "Application") or "--",
        resolution=get_row_string(row, "Resolution") or "--",
        gpu=get_row_string(row, "GPU") or get_row_string(row, "GPU0") or "--",
        cpu=get_row_string(row, "CPU") or "--",
        duration=format_duration(duration_sec),
        frame_count=len(parsed),
    )


def analyze_session(loaded: LoadedCsv, options: AnalysisOptions | None = None) -> SessionAnalysis:
    options = options or AnalysisOptions()
    parsed = build_parsed_samples(loaded.rows)
    catalog = build_metric_catalog(loaded)

    threshold = options.gpu_threshold
    if options.auto_gpu_threshold:
        threshold = compute_auto_gpu_threshold(parsed)

    metadata = extract_metadata(loaded, parsed, threshold, options.trim_buffer_seconds)
    return SessionAnalysis(
        loaded=loaded,
        catalog=catalog,
        parsed=parsed,
        options=AnalysisOptions(
            gpu_threshold=threshold,
            trim_buffer_seconds=options.trim_buffer_seconds,
            auto_gpu_threshold=options.auto_gpu_threshold,
        ),
        metadata=metadata,
    )


def _metric_by_id(catalog: list[MetricDef], metric_id: str) -> MetricDef | None:
    for metric in catalog:
        if metric.metric_id == metric_id:
            return metric
    if metric_id == "fps":
        return CORE_BY_ID["fps"]
    return None


def get_trimmed_series(
    session: SessionAnalysis,
    metric_id: str,
) -> list[ChartPoint]:
    parsed = session.parsed
    if not parsed:
        return []

    metric = _metric_by_id(session.catalog, metric_id)
    if metric is None:
        return []

    threshold = session.options.gpu_threshold
    trim_buffer = normalize_trim_buffer(session.options.trim_buffer_seconds)
    active_window = infer_active_window(parsed, threshold, trim_buffer)
    headers = session.loaded.headers

    bins: dict[int, dict] = {}
    for sample in parsed:
        index = int(sample["t"] // FPS_BIN_SECONDS)
        if index not in bins:
            bins[index] = {
                "start": index * FPS_BIN_SECONDS,
                "fps_frames": 0,
                "fps_total_ms": 0.0,
                "util_sum": 0.0,
                "util_count": 0,
                "value_sum": 0.0,
                "value_count": 0,
            }
        bin_item = bins[index]
        if sample["util"] is not None:
            bin_item["util_sum"] += sample["util"]
            bin_item["util_count"] += 1

        if metric_id == "fps":
            ft = sample["ft"]
            if ft is None or ft <= 0:
                continue
            bin_item["fps_frames"] += 1
            bin_item["fps_total_ms"] += ft
        else:
            value = get_metric_value(sample["row"], metric, headers)
            if value is None:
                continue
            bin_item["value_sum"] += value
            bin_item["value_count"] += 1

    x_origin = active_window["start"] if active_window else parsed[0]["t"]
    points: list[ChartPoint] = []
    for bin_item in sorted(bins.values(), key=lambda b: b["start"]):
        if active_window:
            x = bin_item["start"]
            if x < active_window["start"] or x > active_window["end"]:
                continue

        avg_gpu = (bin_item["util_sum"] / bin_item["util_count"]) if bin_item["util_count"] else None
        if avg_gpu is not None and avg_gpu < threshold:
            continue

        if metric_id == "fps":
            if bin_item["fps_frames"] < MIN_FRAMES_PER_BIN or bin_item["fps_total_ms"] <= 0:
                continue
            y = (1000.0 * bin_item["fps_frames"]) / bin_item["fps_total_ms"]
            if y <= 0 or y > FPS_CHART_CAP:
                continue
            points.append(ChartPoint(x=bin_item["start"] - x_origin, y=y))
        else:
            if bin_item["value_count"] < MIN_FRAMES_PER_BIN:
                continue
            y = bin_item["value_sum"] / bin_item["value_count"]
            points.append(ChartPoint(x=bin_item["start"] - x_origin, y=y))

    if len(points) > 2:
        return points[1:-1]
    return points


def get_stats_from_series(metric_id: str, values: list[float]) -> dict[str, float | None]:
    if not values:
        return {}
    sorted_vals = sorted(values)
    fields = metric_stat_fields(metric_id)
    result: dict[str, float | None] = {}
    for key, _label in fields:
        if key == "avg":
            result["avg"] = mean(values)
        elif key == "min":
            result["min"] = sorted_vals[0]
        elif key == "max":
            result["max"] = sorted_vals[-1]
        elif key == "p1":
            result["p1"] = (
                percentile(sorted_vals, 0.99)
                if metric_id in {"frametime", "latency", "render_present_latency", "until_displayed", "in_present_api", "flip_delay"}
                else percentile(sorted_vals, 0.01)
            )
        elif key == "p01":
            result["p01"] = (
                percentile(sorted_vals, 0.999)
                if metric_id in {"frametime", "latency", "render_present_latency", "until_displayed", "in_present_api", "flip_delay"}
                else percentile(sorted_vals, 0.001)
            )
    return result