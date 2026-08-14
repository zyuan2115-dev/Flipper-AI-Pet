from __future__ import annotations

import json
import os
from pathlib import Path


STATES = ("idle", "thinking", "running", "approval", "success", "error")
MODES = ("off", "solid", "blink", "breathe", "timeout")
SOUNDS = ("none", "single", "double", "triple", "success", "error")
CONFIG_PATH = Path(
    os.getenv("AI_PET_EFFECTS_FILE", "~/.flipper-pet/effects.json")
).expanduser()

DEFAULTS = {
    "idle": {"color": "#000000", "brightness": 0, "mode": "off", "duration": 0, "sound": "none"},
    "thinking": {"color": "#3478cf", "brightness": 100, "mode": "solid", "duration": 0, "sound": "none"},
    "running": {"color": "#ffc000", "brightness": 100, "mode": "solid", "duration": 0, "sound": "none"},
    "approval": {"color": "#a855f7", "brightness": 100, "mode": "breathe", "duration": 0, "sound": "triple"},
    "success": {"color": "#22c55e", "brightness": 100, "mode": "timeout", "duration": 3, "sound": "success"},
    "error": {"color": "#ef4444", "brightness": 100, "mode": "blink", "duration": 0, "sound": "error"},
}


def _validate_effect(value: dict) -> dict:
    color = str(value.get("color", "#000000")).upper()
    if len(color) != 7 or color[0] != "#" or any(c not in "0123456789ABCDEF" for c in color[1:]):
        raise ValueError("颜色必须是 #RRGGBB")
    brightness = int(value.get("brightness", 100))
    duration = int(value.get("duration", 0))
    mode = str(value.get("mode", "solid"))
    sound = str(value.get("sound", "none"))
    if not 0 <= brightness <= 100:
        raise ValueError("亮度必须在 0 到 100 之间")
    if not 0 <= duration <= 60:
        raise ValueError("自动关闭时间必须在 0 到 60 秒之间")
    if mode not in MODES or sound not in SOUNDS:
        raise ValueError("不支持的灯光或蜂鸣模式")
    return {"color": color, "brightness": brightness, "mode": mode, "duration": duration, "sound": sound}


def load_effects() -> dict:
    saved = {}
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            saved = {}
    return {state: _validate_effect(saved.get(state, default)) for state, default in DEFAULTS.items()}


def save_effects(values: dict) -> dict:
    effects = {state: _validate_effect(values.get(state, DEFAULTS[state])) for state in STATES}
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = CONFIG_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(effects, ensure_ascii=False, indent=2) + "\n")
    os.replace(temp, CONFIG_PATH)
    return effects


def command_for(state: str) -> str:
    effect = load_effects()[state]
    color = effect["color"][1:]
    return f'fx {state} {color} {effect["brightness"]} {effect["mode"]} {effect["duration"]} {effect["sound"]}'
