"""Selector compacto y desplazable de métricas FrameView."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

import customtkinter as ctk

from frameview_analyzer.metrics import MetricDef
from frameview_analyzer.ui_helpers import APP_COLORS

CATEGORY_ORDER = ("Rendimiento", "Latencia", "GPU", "CPU", "Energía", "Otros")


class MetricPicker(ctk.CTkFrame):
    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        on_select: Callable[[MetricDef], None],
        list_height: int = 132,
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._on_select = on_select
        self._metrics: list[MetricDef] = []
        self._metric_map: dict[str, MetricDef] = {}
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._selected_id = "fps"

        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.pack(fill="x", pady=(0, 6))
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        self._search = ctk.CTkEntry(
            search_row,
            textvariable=self._search_var,
            placeholder_text="Buscar métrica…",
            height=28,
            font=ctk.CTkFont(size=11),
            border_color=APP_COLORS["card_border"],
        )
        self._search.pack(fill="x")

        self._scroll = ctk.CTkScrollableFrame(
            self,
            height=list_height,
            fg_color="#181818",
            border_color=APP_COLORS["card_border"],
            border_width=1,
            corner_radius=8,
            scrollbar_button_color="#333333",
            scrollbar_button_hover_color="#444444",
        )
        self._scroll.pack(fill="x")
        self._list_inner = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._list_inner.pack(fill="x", anchor="nw")

        self._empty_label = ctk.CTkLabel(
            self._list_inner,
            text="Carga un CSV para ver métricas",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=10),
        )
        self._empty_label.pack(anchor="w", padx=6, pady=8)

    def set_metrics(self, metrics: list[MetricDef], selected_id: str | None = None) -> None:
        self._metrics = list(metrics)
        if selected_id:
            self._selected_id = selected_id
        elif self._metrics and not any(m.metric_id == self._selected_id for m in self._metrics):
            self._selected_id = self._metrics[0].metric_id
        self._apply_filter()

    def get_selected_id(self) -> str:
        return self._selected_id

    def _apply_filter(self) -> None:
        query = self._search_var.get().strip().lower()
        filtered = self._metrics
        if query:
            filtered = [
                m
                for m in self._metrics
                if query in m.label.lower()
                or query in m.category.lower()
                or query in m.metric_id.lower()
            ]
        self._render_list(filtered)

    def _render_list(self, metrics: list[MetricDef]) -> None:
        for child in self._list_inner.winfo_children():
            child.destroy()
        self._buttons.clear()
        self._metric_map.clear()

        if not metrics:
            ctk.CTkLabel(
                self._list_inner,
                text="Sin coincidencias",
                text_color=APP_COLORS["muted"],
                font=ctk.CTkFont(size=10),
            ).pack(anchor="w", padx=6, pady=8)
            return

        grouped: dict[str, list[MetricDef]] = defaultdict(list)
        for metric in metrics:
            grouped[metric.category].append(metric)

        categories = [c for c in CATEGORY_ORDER if c in grouped]
        categories.extend(sorted(k for k in grouped if k not in CATEGORY_ORDER))

        for category in categories:
            ctk.CTkLabel(
                self._list_inner,
                text=category.upper(),
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color=APP_COLORS["accent"],
                anchor="w",
            ).pack(fill="x", padx=4, pady=(6, 2))

            for metric in grouped[category]:
                short = metric.label if len(metric.label) <= 34 else metric.label[:33] + "…"
                unit_suffix = f" · {metric.unit}" if metric.unit else ""
                btn = ctk.CTkButton(
                    self._list_inner,
                    text=f"{short}{unit_suffix}",
                    height=24,
                    font=ctk.CTkFont(size=10),
                    anchor="w",
                    corner_radius=6,
                    border_width=1,
                    fg_color=self._btn_color(metric.metric_id, selected=False),
                    hover_color="#2a2a2a",
                    border_color=self._btn_border(metric.metric_id, selected=False),
                    command=lambda m=metric: self._select(m),
                )
                btn.pack(fill="x", padx=4, pady=1)
                self._buttons[metric.metric_id] = btn
                self._metric_map[metric.metric_id] = metric

        if self._selected_id in self._buttons:
            self._highlight(self._selected_id)

    def _btn_color(self, metric_id: str, selected: bool) -> str:
        if selected:
            return APP_COLORS["accent_dim"]
        return "#1f1f1f"

    def _btn_border(self, metric_id: str, selected: bool) -> str:
        if selected:
            return APP_COLORS["accent"]
        return "#2a2a2a"

    def _highlight(self, metric_id: str) -> None:
        for mid, btn in self._buttons.items():
            selected = mid == metric_id
            btn.configure(
                fg_color=self._btn_color(mid, selected),
                border_color=self._btn_border(mid, selected),
                text_color=APP_COLORS["accent"] if selected else "gray85",
            )

    def _select(self, metric: MetricDef) -> None:
        self._selected_id = metric.metric_id
        self._highlight(metric.metric_id)
        self._on_select(metric)