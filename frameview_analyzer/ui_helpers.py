"""Utilidades visuales para la interfaz del analizador FrameView."""

from __future__ import annotations

import customtkinter as ctk

APP_COLORS = {
    "accent": "#76b900",
    "accent_hover": "#5f9400",
    "accent_dim": "#1a2e0a",
    "success": "#2d8a4e",
    "warning": "#e0a020",
    "danger": "#c44b4b",
    "muted": "gray70",
    "card": "#1e1e1e",
    "card_border": "#333333",
    "chart_bg": "#141414",
    "series_a": "#76b900",
    "series_b": "#3b8ed0",
}

# Colores hex válidos para matplotlib (no acepta nombres tipo gray70 de Tk).
MPL_COLORS = {
    "tick": "#b3b3b3",
    "label": "#b3b3b3",
    "legend": "#d9d9d9",
    "title": "#ffffff",
}


def build_page_header(
    parent: ctk.CTkBaseClass,
    title: str,
    subtitle: str,
    badge: str | None = None,
) -> ctk.CTkFrame:
    header = ctk.CTkFrame(parent, fg_color="transparent")
    header.pack(fill="x", padx=20, pady=(18, 8))

    title_row = ctk.CTkFrame(header, fg_color="transparent")
    title_row.pack(fill="x")
    ctk.CTkLabel(title_row, text=title, font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
    if badge:
        ctk.CTkLabel(
            title_row,
            text=badge,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=APP_COLORS["accent"],
            fg_color=APP_COLORS["accent_dim"],
            corner_radius=6,
            padx=10,
            pady=2,
        ).pack(side="left", padx=(12, 0))

    ctk.CTkLabel(header, text=subtitle, text_color=APP_COLORS["muted"], anchor="w").pack(fill="x", pady=(4, 0))
    return header


def section_header(parent: ctk.CTkBaseClass, title: str) -> ctk.CTkFrame:
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=12, pady=(10, 4))
    ctk.CTkLabel(row, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color="gray85").pack(side="left")
    ctk.CTkFrame(row, fg_color="#333333", height=1).pack(side="left", fill="x", expand=True, padx=(8, 0), pady=6)
    return row


def build_card(parent: ctk.CTkBaseClass, title: str | None = None) -> ctk.CTkFrame:
    card = ctk.CTkFrame(
        parent,
        fg_color=APP_COLORS["card"],
        border_color=APP_COLORS["card_border"],
        border_width=1,
        corner_radius=12,
    )
    if title:
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(
            fill="x", padx=14, pady=(12, 6)
        )
    return card


def format_stat(value: float | None, unit: str = "") -> str:
    if value is None:
        return "--"
    suffix = f" {unit}" if unit else ""
    if abs(value) >= 1000:
        return f"{value:,.0f}{suffix}"
    if abs(value) >= 100:
        return f"{value:.0f}{suffix}"
    return f"{value:.1f}{suffix}"