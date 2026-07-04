"""Panel de gráficos matplotlib embebido en CustomTkinter."""

from __future__ import annotations

from dataclasses import dataclass

import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from frameview_analyzer.analytics import ChartPoint, get_stats_from_series
from frameview_analyzer.metrics import MetricDef, metric_stat_fields, metric_unit
from frameview_analyzer.ui_helpers import APP_COLORS, format_stat


@dataclass
class ChartSeries:
    label: str
    color: str
    points: list[ChartPoint]


class ChartPanel(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._figure = Figure(figsize=(8, 4), dpi=100, facecolor=APP_COLORS["chart_bg"])
        self._axis = self._figure.add_subplot(111)
        self._canvas = FigureCanvasTkAgg(self._figure, master=self)
        self._canvas_widget = self._canvas.get_tk_widget()
        self._canvas_widget.pack(fill="both", expand=True)
        self._empty_label = ctk.CTkLabel(
            self,
            text="Carga un CSV de FrameView para ver el gráfico",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=14),
        )
        self._empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self._style_axis()

    def _style_axis(self) -> None:
        self._axis.set_facecolor(APP_COLORS["chart_bg"])
        self._axis.tick_params(colors="gray70", labelsize=9)
        for spine in self._axis.spines.values():
            spine.set_color("#444444")
        self._axis.grid(True, color="#2a2a2a", linestyle="--", linewidth=0.6, alpha=0.8)

    def clear(self) -> None:
        self._axis.clear()
        self._style_axis()
        self._canvas.draw_idle()
        self._empty_label.lift()

    def render(
        self,
        metric: MetricDef,
        series_list: list[ChartSeries],
        x_label: str = "Tiempo (s)",
    ) -> None:
        self._axis.clear()
        self._style_axis()
        has_data = any(series.points for series in series_list)
        if not has_data:
            self.clear()
            return

        self._empty_label.lower()
        unit = metric_unit(metric)
        y_label = f"{metric.label} ({unit})" if unit else metric.label

        for series in series_list:
            if not series.points:
                continue
            xs = [p.x for p in series.points]
            ys = [p.y for p in series.points]
            self._axis.plot(xs, ys, label=series.label, color=series.color, linewidth=1.6, alpha=0.92)

        self._axis.set_xlabel(x_label, color="gray70", fontsize=10)
        self._axis.set_ylabel(y_label, color="gray70", fontsize=10)
        self._axis.set_title(metric.label, color="white", fontsize=12, pad=10)
        if len(series_list) > 1:
            legend = self._axis.legend(facecolor="#222222", edgecolor="#444444", labelcolor="gray85", fontsize=9)
            legend.get_frame().set_alpha(0.95)
        self._figure.tight_layout()
        self._canvas.draw_idle()

    def export_png(self, path: str) -> None:
        self._figure.savefig(path, dpi=160, facecolor=APP_COLORS["chart_bg"])


class StatsPanel(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._columns = ctk.CTkFrame(self, fg_color="transparent")
        self._columns.pack(fill="x", expand=True)
        self._base_col = ctk.CTkFrame(self._columns, fg_color="transparent")
        self._comp_col = ctk.CTkFrame(self._columns, fg_color="transparent")
        self._delta_col = ctk.CTkFrame(self._columns, fg_color="transparent")
        self._base_col.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self._comp_col.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self._delta_col.pack(side="left", fill="both", expand=True)

    def clear(self) -> None:
        for col in (self._base_col, self._comp_col, self._delta_col):
            for child in col.winfo_children():
                child.destroy()

    def render(
        self,
        metric: MetricDef,
        base_label: str,
        base_values: list[float],
        comp_label: str | None = None,
        comp_values: list[float] | None = None,
    ) -> None:
        self.clear()
        unit = metric_unit(metric)
        base_stats = get_stats_from_series(metric.metric_id, base_values)
        comp_stats = get_stats_from_series(metric.metric_id, comp_values or []) if comp_values else None
        fields = metric_stat_fields(metric.metric_id)

        self._render_column(self._base_col, base_label, APP_COLORS["series_a"], fields, base_stats, unit)
        if comp_stats:
            self._render_column(self._comp_col, comp_label or "Comparativa", APP_COLORS["series_b"], fields, comp_stats, unit)
            self._render_delta(self._delta_col, metric, fields, base_stats, comp_stats, unit)
        else:
            ctk.CTkLabel(
                self._comp_col,
                text="Sin sesión comparativa",
                text_color=APP_COLORS["muted"],
            ).pack(anchor="w", pady=8)

    def _render_column(
        self,
        parent: ctk.CTkFrame,
        title: str,
        color: str,
        fields: list[tuple[str, str]],
        stats: dict[str, float | None],
        unit: str,
    ) -> None:
        ctk.CTkLabel(parent, text=title, text_color=color, font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        for key, label in fields:
            value = stats.get(key)
            ctk.CTkLabel(
                parent,
                text=f"{label}: {format_stat(value, unit)}",
                text_color="gray85",
                font=ctk.CTkFont(size=12),
            ).pack(anchor="w", pady=1)

    def _render_delta(
        self,
        parent: ctk.CTkFrame,
        metric: MetricDef,
        fields: list[tuple[str, str]],
        base_stats: dict[str, float | None],
        comp_stats: dict[str, float | None],
        unit: str,
    ) -> None:
        ctk.CTkLabel(parent, text="Delta", text_color="gray70", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        lower_is_better = metric.higher_is_better is False
        for key, label in fields:
            base_val = base_stats.get(key)
            comp_val = comp_stats.get(key)
            if base_val is None or comp_val is None:
                text = f"{label}: --"
                color = APP_COLORS["muted"]
            else:
                delta = comp_val - base_val
                pct = (delta / abs(base_val) * 100) if base_val else 0.0
                sign = "+" if delta >= 0 else ""
                text = f"{label}: {sign}{delta:.1f} {unit} ({sign}{pct:.1f}%)"
                improved = delta < 0 if lower_is_better else delta > 0
                color = APP_COLORS["success"] if improved else APP_COLORS["danger"] if abs(delta) > 0.05 else "gray70"
            ctk.CTkLabel(parent, text=text, text_color=color, font=ctk.CTkFont(size=12)).pack(anchor="w", pady=1)