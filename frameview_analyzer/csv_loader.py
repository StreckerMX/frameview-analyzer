"""Carga y detección de archivos CSV exportados por NVIDIA FrameView."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

NA_VALUES = {"", "NA", "N/A", "n/a", "null", "NULL"}


@dataclass(frozen=True)
class LoadedCsv:
    path: Path
    kind: str  # "log" | "summary" | "unknown"
    headers: list[str]
    rows: list[dict[str, str]]
    display_name: str


def sanitize_display_name(filename: str) -> str:
    name = Path(filename).stem
    name = re.sub(r"^FrameView_", "", name)
    name = re.sub(r"_Log$", "", name)
    if len(name) > 40:
        return name[:39] + "…"
    return name


def detect_csv_kind(headers: list[str], filename: str = "") -> str:
    normalized = [h.strip() for h in headers]
    if "TimeInSeconds" in normalized or "MsBetweenPresents" in normalized:
        return "log"
    if "Avg FPS" in normalized and "Log Name" in normalized:
        return "summary"
    if filename and re.search(r"summary", filename, re.IGNORECASE):
        return "summary"
    return "unknown"


def _clean_cell(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def load_csv(path: Path | str) -> LoadedCsv:
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = [{k: _clean_cell(v) for k, v in row.items()} for row in reader]

    kind = detect_csv_kind(headers, path.name)
    return LoadedCsv(
        path=path,
        kind=kind,
        headers=headers,
        rows=rows,
        display_name=sanitize_display_name(path.name),
    )


def get_numeric(row: dict[str, str], keys: list[str]) -> float | None:
    for key in keys:
        if key not in row:
            continue
        raw = row[key]
        if raw in NA_VALUES:
            continue
        try:
            value = float(raw.replace(",", "."))
        except (TypeError, ValueError):
            continue
        if value == value:  # not NaN
            return value
    return None


def get_row_string(row: dict[str, str], key: str) -> str | None:
    if key not in row:
        return None
    value = row[key].strip()
    if value in NA_VALUES:
        return None
    return value


def is_numeric_column(rows: list[dict[str, str]], column: str, sample_size: int = 200) -> bool:
    checked = 0
    numeric_hits = 0
    for row in rows[:sample_size]:
        raw = row.get(column, "")
        if raw in NA_VALUES:
            continue
        checked += 1
        try:
            float(raw.replace(",", "."))
            numeric_hits += 1
        except ValueError:
            return False
    return checked > 0 and numeric_hits == checked