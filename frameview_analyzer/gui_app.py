"""Interfaz gráfica del analizador NVIDIA FrameView."""

from __future__ import annotations

import tkinter as tk
from collections import defaultdict
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from frameview_analyzer.analytics import (
    AnalysisOptions,
    SessionAnalysis,
    analyze_session,
    get_trimmed_series,
)
from frameview_analyzer.chart_panel import ChartPanel, ChartSeries, StatsPanel
from frameview_analyzer.csv_loader import LoadedCsv, load_csv
from frameview_analyzer.metrics import MetricDef
from frameview_analyzer.ui_helpers import APP_COLORS, build_card, build_page_header

METRIC_HELP = {
    "fps": "FPS calculado por segundo en el tramo activo de la prueba.",
    "frametime": "Milisegundos entre presents. Más bajo y estable = más fluido.",
    "latency": "Latencia de PC (MsPCLatency). Menor = respuesta más directa.",
    "fg_multiplier": "Multiplicador Frame Generation. 1 = nativo.",
    "gpu0_util": "Uso de GPU principal. Ayuda a filtrar menús o carga.",
    "cpu_util": "Uso de CPU. Útil para detectar cuello de botella.",
    "gpu0_temp": "Temperatura de la GPU en el tramo activo.",
}


class FrameViewAnalyzerApp(ctk.CTk):
    def __init__(self, app_dir: Path):
        super().__init__()
        self.app_dir = app_dir
        self.title("FrameView Analyzer")
        self.geometry("1280x860")
        self.minsize(1080, 720)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._session_a: SessionAnalysis | None = None
        self._session_b: SessionAnalysis | None = None
        self._metric_map: dict[str, MetricDef] = {}
        self._selected_metric_id = "fps"

        self._build_ui()
        self._refresh_dashboard()

    def _build_ui(self) -> None:
        build_page_header(
            self,
            "FrameView Analyzer",
            "Analiza logs CSV de NVIDIA FrameView: FPS, latencia, GPU, CPU y todas las métricas exportadas.",
            badge="NVIDIA FrameView",
        )

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=20, pady=(0, 8))

        self._btn_load_a = ctk.CTkButton(
            toolbar,
            text="Cargar sesión base",
            fg_color=APP_COLORS["accent"],
            hover_color=APP_COLORS["accent_hover"],
            command=lambda: self._load_session(slot="a"),
        )
        self._btn_load_a.pack(side="left", padx=(0, 8))

        self._btn_load_b = ctk.CTkButton(
            toolbar,
            text="Cargar comparativa",
            fg_color="#2a2a2a",
            hover_color="#3a3a3a",
            border_color=APP_COLORS["series_b"],
            border_width=1,
            command=lambda: self._load_session(slot="b"),
        )
        self._btn_load_b.pack(side="left", padx=(0, 8))

        self._btn_export = ctk.CTkButton(
            toolbar,
            text="Exportar gráfico PNG",
            fg_color="#2a2a2a",
            hover_color="#3a3a3a",
            command=self._export_chart,
        )
        self._btn_export.pack(side="left")

        self._file_a_label = ctk.CTkLabel(toolbar, text="Base: sin archivo", text_color=APP_COLORS["muted"])
        self._file_a_label.pack(side="right", padx=(8, 0))
        self._file_b_label = ctk.CTkLabel(toolbar, text="Comparativa: --", text_color=APP_COLORS["muted"])
        self._file_b_label.pack(side="right", padx=(8, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkScrollableFrame(body, width=300, fg_color=APP_COLORS["card"], corner_radius=12)
        sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 12))

        ctk.CTkLabel(sidebar, text="Métrica", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(12, 4))
        self._metric_var = tk.StringVar(value="fps")
        self._metric_menu = ctk.CTkOptionMenu(
            sidebar,
            variable=self._metric_var,
            values=["fps"],
            command=self._on_metric_changed,
            width=260,
        )
        self._metric_menu.pack(padx=12, pady=(0, 8))

        self._metric_help = ctk.CTkLabel(
            sidebar,
            text=METRIC_HELP["fps"],
            text_color=APP_COLORS["muted"],
            wraplength=250,
            justify="left",
            font=ctk.CTkFont(size=11),
        )
        self._metric_help.pack(anchor="w", padx=12, pady=(0, 12))

        ctk.CTkLabel(sidebar, text="Filtro de tramo activo", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=12, pady=(4, 4)
        )

        self._auto_gpu_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            sidebar,
            text="Umbral GPU automático",
            variable=self._auto_gpu_var,
            command=self._refresh_dashboard,
        ).pack(anchor="w", padx=12, pady=(0, 6))

        gpu_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        gpu_row.pack(fill="x", padx=12, pady=(0, 6))
        ctk.CTkLabel(gpu_row, text="Umbral GPU %").pack(side="left")
        self._gpu_threshold = ctk.CTkSlider(gpu_row, from_=0, to=80, number_of_steps=80, command=self._on_slider)
        self._gpu_threshold.set(10)
        self._gpu_threshold.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._gpu_value_label = ctk.CTkLabel(gpu_row, text="10", width=28)
        self._gpu_value_label.pack(side="left")

        trim_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        trim_row.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkLabel(trim_row, text="Recorte bordes s").pack(side="left")
        self._trim_buffer = ctk.CTkSlider(trim_row, from_=0, to=10, number_of_steps=10, command=self._on_slider)
        self._trim_buffer.set(1)
        self._trim_buffer.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._trim_value_label = ctk.CTkLabel(trim_row, text="1", width=28)
        self._trim_value_label.pack(side="left")

        self._metadata_card = build_card(sidebar, "Sesión base")
        self._metadata_card.pack(fill="x", padx=8, pady=(0, 8))
        self._meta_a_text = ctk.CTkLabel(
            self._metadata_card,
            text="Sin datos",
            justify="left",
            anchor="w",
            text_color="gray85",
            font=ctk.CTkFont(size=11),
        )
        self._meta_a_text.pack(fill="x", padx=12, pady=(0, 12))

        self._metadata_b_card = build_card(sidebar, "Comparativa")
        self._metadata_b_card.pack(fill="x", padx=8, pady=(0, 12))
        self._meta_b_text = ctk.CTkLabel(
            self._metadata_b_card,
            text="Sin datos",
            justify="left",
            anchor="w",
            text_color="gray85",
            font=ctk.CTkFont(size=11),
        )
        self._meta_b_text.pack(fill="x", padx=12, pady=(0, 12))

        main = ctk.CTkFrame(body, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(0, weight=3)
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        chart_card = build_card(main, "Gráfico temporal")
        chart_card.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self._chart = ChartPanel(chart_card)
        self._chart.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        stats_card = build_card(main, "Estadísticas del tramo activo")
        stats_card.grid(row=1, column=0, sticky="nsew")
        self._stats = StatsPanel(stats_card)
        self._stats.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _on_slider(self, _value: float) -> None:
        self._gpu_value_label.configure(text=str(int(round(self._gpu_threshold.get()))))
        self._trim_value_label.configure(text=str(int(round(self._trim_buffer.get()))))
        self._refresh_dashboard()

    def _on_metric_changed(self, metric_id: str) -> None:
        self._selected_metric_id = metric_id
        self._metric_help.configure(text=METRIC_HELP.get(metric_id, "Métrica numérica exportada por FrameView."))
        self._refresh_dashboard()

    def _analysis_options(self) -> AnalysisOptions:
        return AnalysisOptions(
            gpu_threshold=float(self._gpu_threshold.get()),
            trim_buffer_seconds=float(self._trim_buffer.get()),
            auto_gpu_threshold=self._auto_gpu_var.get(),
        )

    def _load_session(self, slot: str) -> None:
        initial = Path.home() / "Documents" / "FrameView"
        path = filedialog.askopenfilename(
            title="Seleccionar CSV de FrameView",
            initialdir=str(initial if initial.exists() else self.app_dir),
            filetypes=[("CSV FrameView", "*.csv"), ("Todos", "*.*")],
        )
        if not path:
            return
        try:
            loaded = load_csv(path)
            if loaded.kind != "log":
                messagebox.showerror(
                    "Archivo no compatible",
                    "Selecciona un archivo *_Log.csv con columnas TimeInSeconds / MsBetweenPresents.",
                )
                return
            session = analyze_session(loaded, self._analysis_options())
        except Exception as exc:
            messagebox.showerror("Error al cargar CSV", str(exc))
            return

        if slot == "a":
            self._session_a = session
            self._file_a_label.configure(text=f"Base: {loaded.display_name}")
        else:
            self._session_b = session
            self._file_b_label.configure(text=f"Comparativa: {loaded.display_name}")

        self._rebuild_metric_menu()
        self._refresh_dashboard()

    def _rebuild_metric_menu(self) -> None:
        catalog = self._session_a.catalog if self._session_a else []
        grouped: dict[str, list[MetricDef]] = defaultdict(list)
        for metric in catalog:
            grouped[metric.category].append(metric)

        labels: list[str] = []
        self._metric_map = {}
        for category in sorted(grouped):
            for metric in grouped[category]:
                label = f"[{category}] {metric.label}"
                labels.append(label)
                self._metric_map[label] = metric

        if not labels:
            labels = ["fps"]
            self._metric_map = {}
            self._selected_metric_id = "fps"
            self._metric_var.set("fps")
            self._metric_menu.configure(values=["fps"])
            return

        self._metric_menu.configure(values=labels)
        current = next((lbl for lbl, m in self._metric_map.items() if m.metric_id == self._selected_metric_id), labels[0])
        self._metric_var.set(current)
        self._selected_metric_id = self._metric_map[current].metric_id

    def _current_metric(self) -> MetricDef | None:
        label = self._metric_var.get()
        if label in self._metric_map:
            return self._metric_map[label]
        if self._session_a:
            for metric in self._session_a.catalog:
                if metric.metric_id == self._selected_metric_id:
                    return metric
        return None

    def _format_metadata(self, session: SessionAnalysis | None) -> str:
        if not session or not session.metadata:
            return "Sin datos"
        meta = session.metadata
        return (
            f"App: {meta.application}\n"
            f"Resolución: {meta.resolution}\n"
            f"GPU: {meta.gpu}\n"
            f"CPU: {meta.cpu}\n"
            f"Duración activa: {meta.duration}\n"
            f"Frames: {meta.frame_count:,}"
        )

    def _refresh_dashboard(self) -> None:
        options = self._analysis_options()
        if self._session_a:
            self._session_a = analyze_session(self._session_a.loaded, options)
        if self._session_b:
            self._session_b = analyze_session(self._session_b.loaded, options)

        self._meta_a_text.configure(text=self._format_metadata(self._session_a))
        self._meta_b_text.configure(text=self._format_metadata(self._session_b))

        metric = self._current_metric()
        if not metric or not self._session_a:
            self._chart.clear()
            self._stats.clear()
            return

        self._selected_metric_id = metric.metric_id
        series: list[ChartSeries] = []
        base_points = get_trimmed_series(self._session_a, metric.metric_id)
        series.append(
            ChartSeries(
                label=self._session_a.loaded.display_name,
                color=APP_COLORS["series_a"],
                points=base_points,
            )
        )
        base_values = [p.y for p in base_points]

        comp_values: list[float] | None = None
        comp_label = None
        if self._session_b:
            comp_points = get_trimmed_series(self._session_b, metric.metric_id)
            series.append(
                ChartSeries(
                    label=self._session_b.loaded.display_name,
                    color=APP_COLORS["series_b"],
                    points=comp_points,
                )
            )
            comp_values = [p.y for p in comp_points]
            comp_label = self._session_b.loaded.display_name

        self._chart.render(metric, series)
        self._stats.render(metric, self._session_a.loaded.display_name, base_values, comp_label, comp_values)

        if self._session_a and self._session_a.options.auto_gpu_threshold:
            threshold = int(round(self._session_a.options.gpu_threshold))
            self._gpu_threshold.set(threshold)
            self._gpu_value_label.configure(text=str(threshold))

    def _export_chart(self) -> None:
        if not self._session_a:
            messagebox.showinfo("Exportar", "Carga al menos una sesión base.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            initialfile=f"frameview_{self._selected_metric_id}.png",
        )
        if not path:
            return
        try:
            self._chart.export_png(path)
            messagebox.showinfo("Exportar", f"Gráfico guardado en:\n{path}")
        except Exception as exc:
            messagebox.showerror("Exportar", str(exc))


def run_gui(app_dir: Path) -> None:
    app = FrameViewAnalyzerApp(app_dir)
    app.mainloop()