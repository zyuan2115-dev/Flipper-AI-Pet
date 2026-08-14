from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from .settings import load_settings


HOME = Path(os.getenv("AI_STATE_HOME", str(Path.home()))).expanduser()
AGENTS = {
    "claude": ("Claude Code", HOME / ".claude" / "settings.json", ("claude",)),
    "codex": ("Codex", HOME / ".codex" / "hooks.json", ("codex",)),
    "cursor": ("Cursor", HOME / ".cursor" / "hooks.json", ("cursor",)),
    "copilot": ("GitHub Copilot", HOME / ".copilot" / "hooks.json", ("gh", "copilot")),
    "qoder": ("Qoder", HOME / ".qoder" / "hooks.json", ("qoder",)),
}
CODEX_APPROVAL_SCRIPT = HOME / ".codex" / "codex-flipper-hook.sh"


def _is_ai_pet_hook(value: object) -> bool:
    content = json.dumps(value, ensure_ascii=False)
    return "ai-state-hub hook" in content or "codex-flipper-hook.sh" in content


def _available(commands: tuple[str, ...]) -> bool:
    return any(shutil.which(command) for command in commands)


def list_agents() -> list[dict]:
    result = []
    for agent_id, (name, path, commands) in AGENTS.items():
        content = path.read_text(errors="ignore") if path.exists() else ""
        result.append({
            "id": agent_id,
            "name": name,
            "available": _available(commands),
            "installed": "ai-state-hub hook" in content or "codex-flipper-hook.sh" in content,
            "config": str(path),
        })
    return result


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"配置根节点不是对象: {path}")
    return value


def reconfigure_codex_approval() -> dict:
    name, path, _ = AGENTS["codex"]
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _load(path)
    hooks = data.setdefault("hooks", {})
    entries = hooks.setdefault("PermissionRequest", [])
    entries[:] = [entry for entry in entries if not _is_ai_pet_hook(entry)]
    mode = load_settings()["approval_mode"]
    if CODEX_APPROVAL_SCRIPT.is_file():
        command = f"zsh '{CODEX_APPROVAL_SCRIPT}' PermissionRequest # ai-state-hub hook"
    else:
        command = "python3 -m ai_state_hub.codex_approval_hook # ai-state-hub hook"
    entries.append({"matcher": ".*", "hooks": [{"type": "command", "command": command}]})
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    os.replace(temp, path)
    return {"ok": True, "agent": name, "config": str(path), "approval_mode": mode}


def install(agent_id: str, port: int) -> dict:
    if agent_id not in AGENTS:
        raise ValueError("不支持的 AI 工具")
    name, path, _ = AGENTS[agent_id]
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if path.exists():
        backup = path.with_name(f"{path.name}.ai-state-backup-{time.strftime('%Y%m%d%H%M%S')}")
        shutil.copy2(path, backup)
    data = _load(path)
    hooks = data.setdefault("hooks", {})
    events = (
        ("SessionStart", "thinking"),
        ("UserPromptSubmit", "thinking"),
        ("PreToolUse", "running"),
        ("PostToolUse", "thinking"),
        ("PermissionRequest", "approval"),
        ("Stop", "success"),
        ("SessionEnd", "idle"),
    )
    for event, state in events:
        if agent_id == "codex" and event == "PermissionRequest":
            if CODEX_APPROVAL_SCRIPT.is_file():
                command = f"zsh '{CODEX_APPROVAL_SCRIPT}' PermissionRequest # ai-state-hub hook"
            else:
                command = "python3 -m ai_state_hub.codex_approval_hook # ai-state-hub hook"
        else:
            command = (
                f'python3 -m ai_state_hub.hook --port {port} '
                f'--agent {agent_id} --event {event} --state {state} # ai-state-hub hook'
            )
        entries = hooks.setdefault(event, [])
        entries[:] = [entry for entry in entries if not _is_ai_pet_hook(entry)]
        hook = {"type": "command", "command": command}
        if not (agent_id == "codex" and event == "PermissionRequest"):
            hook["timeoutSec"] = 3
        item = {"hooks": [hook]}
        if event in ("PreToolUse", "PostToolUse", "PermissionRequest"):
            item["matcher"] = ".*" if agent_id == "codex" else "*"
        entries.append(item)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    os.replace(temp, path)
    return {"ok": True, "agent": name, "config": str(path), "backup": str(backup) if backup else None}
