from __future__ import annotations

from pathlib import Path


def default_reports_root() -> Path:
    return Path.home() / "Downloads" / "PHR Diff Reports"
