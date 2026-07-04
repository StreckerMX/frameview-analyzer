#!/usr/bin/env python3
"""Interfaz gráfica de FrameView Analyzer."""

from __future__ import annotations

import sys
from pathlib import Path

from frameview_analyzer.gui_app import run_gui


def main() -> int:
    run_gui(Path(__file__).parent)
    return 0


if __name__ == "__main__":
    sys.exit(main())