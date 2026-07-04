from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any

import pandas as pd


class InputLoader:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.config_path = self.base_dir / "config" / "mappings.json"
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def load_phr_excel(self, file_path: str) -> pd.DataFrame:
        sheet = self.config["phr_excel"]["sheet"]
        df = pd.read_excel(file_path, sheet_name=sheet)
        renamed = {}
        for target, source in self.config["phr_excel"]["columns"].items():
            if source in df.columns:
                renamed[target] = df[source]
        return pd.DataFrame(renamed)

    def load_psd_excel(self, file_path: str) -> pd.DataFrame:
        sheet = self.config["psd_excel"]["sheet"]
        df = pd.read_excel(file_path, sheet_name=sheet)
        renamed = {}
        for target, source in self.config["psd_excel"]["columns"].items():
            if source in df.columns:
                renamed[target] = df[source]
        return pd.DataFrame(renamed)
