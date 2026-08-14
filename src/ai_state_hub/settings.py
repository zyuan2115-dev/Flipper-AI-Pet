from __future__ import annotations

import json
import os
from pathlib import Path


APPROVAL_MODES = ("full", "none", "handoff")
CONFIG_PATH = Path(
    os.getenv("AI_PET_SETTINGS_FILE", "~/.flipper-pet/settings.json")
).expanduser()
DEFAULTS = {"approval_mode": "handoff", "approval_timeout_seconds": 5}


def load_settings() -> dict:
    saved = {}
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            saved = {}
    mode = str(saved.get("approval_mode", DEFAULTS["approval_mode"]))
    if mode == "handoff_5s":
        mode = "handoff"
    if mode not in APPROVAL_MODES:
        mode = DEFAULTS["approval_mode"]
    try:
        timeout = int(saved.get("approval_timeout_seconds", DEFAULTS["approval_timeout_seconds"]))
    except (TypeError, ValueError):
        timeout = DEFAULTS["approval_timeout_seconds"]
    if not 1 <= timeout <= 300:
        timeout = DEFAULTS["approval_timeout_seconds"]
    return {"approval_mode": mode, "approval_timeout_seconds": timeout}


def save_settings(value: dict) -> dict:
    mode = str(value.get("approval_mode", ""))
    if mode == "handoff_5s":
        mode = "handoff"
    if mode not in APPROVAL_MODES:
        raise ValueError("不支持的 AI Pet 接管模式")
    try:
        timeout = int(value.get("approval_timeout_seconds", DEFAULTS["approval_timeout_seconds"]))
    except (TypeError, ValueError) as error:
        raise ValueError("响应转移秒数必须是整数") from error
    if not 1 <= timeout <= 300:
        raise ValueError("响应转移秒数必须在 1 到 300 秒之间")
    settings = {"approval_mode": mode, "approval_timeout_seconds": timeout}
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = CONFIG_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n")
    os.replace(temp, CONFIG_PATH)
    return settings
