"""Panel de gráficos matplotlib embebido en CustomTkinter."""

from __future__ import annotations

from dataclasses import dataclass

import customtkinter as ctk
import matplotlib.ticker as mticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from frameview_analyzer.analytics import ChartPoint, get_stats_from_series, mean
from frameview_analyzer.metrics import MetricDef, metric_stat_fields, metric_unit
from frameview_analyzer.ui_helpers import APP_COLORS, MPL_COLORS, format_stat


@dataclass
class ChartSeries:
    label: str
    color: str
    points: list[ChartPoint]


class ChartPanel(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._figure = Figure(figsize=(9, 4.2), dpi=100, facecolor=APP_COLORS["chart_bg"])
        self._figure.subplots_adjust(left=0.07, right=0.98, top=0.90, bottom=0.14)
        self._axis = self._figure.add_subplot(111)
        self._canvas = FigureCanvasTkAgg(self._figure, master=self)
        self._canvas_widget = self._canvas.get_tk_widget()
        self._canvas_widget.configure(bg=APP_COLORS["chart_bg"], highlightthickness=0)
        self._canvas_widget.pack(fill="both", expand=True)
        self._empty_label = ctk.CTkLabel(
            self,
            text="Carga un CSV de FrameView para ver el gráfico",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=13),
        )
        self._empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self._style_axis()

    def _style_axis(self) -> None:
        self._axis.set_facecolor(APP_COLORS["chart_bg"])
        self._axis.tick_params(colors=MPL_COLORS["tick"], labelsize=8, length=3, width=0.6)
        for spine in self._axis.spines.values():
            spine.set_visible(False)
        self._axis.grid(True, color="#252525", linestyle="-", linewidth=0.5, alpha=0.9)
        self._axis.set_axisbelow(True)

    def clear(self) -> None:
        self._axis.clear()
        self._style_axis()
        self._canvas.draw_idle()
        self._empty_label.lift()

    def _format_y_axis(self, values: list[float]) -> None:
        if not values:
            return
        span = max(values) - min(values)
        if span >= 500:
            self._axis.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _p: f"{v:,.0f}"))
        elif span >= 20:
            self._axis.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _p: f"{v:.0f}"))
        else:
            self._axis.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _p: f"{v:.1f}"))

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
        all_ys: list[float] = []

        for index, series in enumerate(series_list):
            if not series.points:
                continue
            xs = [p.x for p in series.points]
            ys = [p.y for p in series.points]
            all_ys.extend(ys)

            self._axis.plot(
                xs,
                ys,
                label=series.label,
                color=series.color,
                linewidth=2.0 if index == 0 else 1.7,
                alpha=0.95,
                solid_capstyle="round",
                zorder=3,
            )

            if len(series_list) == 1:
                self._axis.fill_between(xs, ys, color=series.color, alpha=0.10, zorder=2)

            avg = mean(ys)
            if avg is not None:
                self._axis.axhline(
                    avg,
                    color=series.color,
                    linestyle=(0, (4, 4)),
                    linewidth=0.9,
                    alpha=0.45,
                    zorder=1,
                )

        self._format_y_axis(all_ys)
        self._axis.set_xlabel(x_label, color=MPL_COLORS["label"], fontsize=9, labelpad=6)
        self._axis.set_ylabel(y_label, color=MPL_COLORS["label"], fontsize=9, labelpad=8)
        self._axis.set_title(metric.label, color=MPL_COLORS["title"], fontsize=11, fontweight="bold", pad=8)

        if len(series_list) > 1:
            legend = self._axis.legend(
                loc="upper right",
                facecolor="#1a1a1a",
                edgecolor="#333333",
                labelcolor=MPL_COLORS["legend"],
                fontsize=8,
                framealpha=0.92,
                borderpad=0.6,
            )
            legend.get_frame().set_linewidth(0.6)

        self._canvas.draw_idle()

    def export_png(self, path: str) -> None:
        self._figure.savefig(path, dpi=180, facecolor=APP_COLORS["chart_bg"], bbox_inches="tight")


class StatsPanel(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._columns = ctk.CTkFrame(self, fg_color="transparent")
        self._columns.pack(fill="both", expand=True)
        self._base_col = ctk.CTkFrame(self._columns, fg_color="transparent")
        self._comp_col = ctk.CTkFrame(self._columns, fg_color="transparent")
        self._delta_col = ctk.CTkFrame(self._columns, fg_color="transparent")
        self._base_col.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self._comp_col.pack(side="left", fill="both", expand=True, padx=(0, 6))
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
                font=ctk.CTkFont(size=11),
            ).pack(anchor="w", pady=8)

    def _stat_chip(self, parent: ctk.CTkFrame, label: str, value: str, value_color: str = "gray90") -> None:
        chip = ctk.CTkFrame(parent, fg_color="#252525", corner_radius=8, border_color="#333333", border_width=1)
        chip.pack(fill="x", pady=2)
        row = ctk.CTkFrame(chip, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=5)
        ctk.CTkLabel(row, text=label, text_color=APP_COLORS["muted"], font=ctk.CTkFont(size=10)).pack(side="left")
        ctk.CTkLabel(
            row,
            text=value,
            text_color=value_color,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="right")

    def _render_column(
        self,
        parent: ctk.CTkFrame,
        title: str,
        color: str,
        fields: list[tuple[str, str]],
        stats: dict[str, float | None],
        unit: str,
    ) -> None:
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(header, text="●", text_color=color, font=ctk.CTkFont(size=10)).pack(side="left")
        ctk.CTkLabel(
            header,
            text=title,
            text_color=color,
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        ).pack(side="left", padx=(2, 0))

        for key, label in fields:
            value = stats.get(key)
            self._stat_chip(parent, label, format_stat(value, unit))

    def _render_delta(
        self,
        parent: ctk.CTkFrame,
        metric: MetricDef,
        fields: list[tuple[str, str]],
        base_stats: dict[str, float | None],
        comp_stats: dict[str, float | None],
        unit: str,
    ) -> None:
        ctk.CTkLabel(parent, text="Delta", text_color=APP_COLORS["muted"], font=ctk.CTkFont(size=11, weight="bold")).pack(
            anchor="w", pady=(0, 4)
        )
        lower_is_better = metric.higher_is_better is False
        for key, label in fields:
            base_val = base_stats.get(key)
            comp_val = comp_stats.get(key)
            if base_val is None or comp_val is None:
                text = "--"
                color = APP_COLORS["muted"]
            else:
                delta = comp_val - base_val
                pct = (delta / abs(base_val) * 100) if base_val else 0.0
                sign = "+" if delta >= 0 else ""
                text = f"{sign}{delta:.1f} {unit} ({sign}{pct:.1f}%)"
                improved = delta < 0 if lower_is_better else delta > 0
                color = APP_COLORS["success"] if improved else APP_COLORS["danger"] if abs(delta) > 0.05 else "gray70"
            self._stat_chip(parent, label, text, value_color=color)