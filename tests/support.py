from __future__ import annotations

import importlib
import os
import shutil
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT / ".unit_tmp"


def make_temp_dir() -> Path:
    TMP_ROOT.mkdir(exist_ok=True)
    path = TMP_ROOT / f"case-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def cleanup_temp_root() -> None:
    shutil.rmtree(TMP_ROOT, ignore_errors=True)


def prepare_storage_module(tmp_path: Path):
    import app.storage as storage_mod

    storage_mod.DATA_DIR = tmp_path
    storage_mod.DATA_FILE = tmp_path / "progress.json"
    return storage_mod


def load_bot_module(tmp_path: Path):
    prepare_storage_module(tmp_path)
    os.environ["OPENAI_API_KEY"] = ""
    sys.modules.pop("app.bot", None)
    return importlib.import_module("app.bot")
