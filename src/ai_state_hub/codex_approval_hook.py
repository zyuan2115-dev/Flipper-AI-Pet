from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import sys
import time
from pathlib import Path
from typing import Any

try:
    from .settings import load_settings
except ImportError:
    from settings import load_settings
try:
    from .effects import command_for
except ImportError:
    try:
        from effects import command_for
    except ImportError:
        command_for = None


SOCKET = Path(os.getenv("FLIPPER_STATE_SOCKET", "/tmp/flipper-state.sock"))
MAX_SUMMARY_BYTES = 32


def request_id(payload: dict[str, Any]) -> str:
    identity = {
        "session_id": payload.get("session_id"),
        "turn_id": payload.get("turn_id"),
        "tool_name": payload.get("tool_name"),
        "tool_input": payload.get("tool_input"),
    }
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()[:16]


def _fit_ascii(value: str, limit: int = MAX_SUMMARY_BYTES) -> str:
    value = value.encode("ascii", errors="ignore").decode()
    value = re.sub(r"\s+", " ", value).strip()
    return value.encode()[:limit].decode(errors="ignore").rstrip()


def request_summary(payload: dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    command = tool_input.get("command")
    if isinstance(command, str):
        summary = _fit_ascii(command)
        if summary:
            return summary
    description = tool_input.get("description")
    if isinstance(description, str):
        summary = _fit_ascii(description)
        if summary:
            return summary
    return _fit_ascii(str(payload.get("tool_name") or "AI permission request"))


def wait_for_decision(payload: dict[str, Any], mode: str) -> str | None:
    approval_id = request_id(payload)
    command = f"approval_req {approval_id} {request_summary(payload)}\n".encode()
    started = time.monotonic()
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(0.25)
            client.connect(str(SOCKET))
            client.sendall(command)
            response = bytearray()
            while not response.endswith(b"\n"):
                current_settings = load_settings()
                current_mode = current_settings["approval_mode"]
                elapsed = time.monotonic() - started
                if current_mode == "none" or (
                    current_mode == "handoff" and
                    elapsed >= current_settings["approval_timeout_seconds"]
                ):
                    handoff_approval(approval_id)
                    return None
                try:
                    chunk = client.recv(256)
                except TimeoutError:
                    continue
                if not chunk:
                    return None
                response.extend(chunk)
    except OSError:
        return None
    parts = response.decode(errors="replace").strip().split()
    if len(parts) == 3 and parts[:2] == ["decision:", approval_id]:
        if parts[2] in ("allow", "deny"):
            return parts[2]
    return None


def handoff_approval(approval_id: str) -> None:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(1)
            client.connect(str(SOCKET))
            client.sendall(f"approval_handoff {approval_id}\n".encode())
            client.recv(128)
    except OSError:
        pass


def notify_approval() -> None:
    command = command_for("approval") if command_for is not None else "approval"
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(0.5)
            client.connect(str(SOCKET))
            client.sendall(f"{command}\n".encode())
            client.recv(128)
    except OSError:
        pass


def codex_output(decision: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {
                "behavior": decision,
                "message": "Approved on AI Pet" if decision == "allow" else "Denied on AI Pet",
            },
        }
    }


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return
    if not isinstance(payload, dict) or payload.get("hook_event_name") != "PermissionRequest":
        return
    mode = load_settings()["approval_mode"]
    if mode == "none":
        notify_approval()
        return
    decision = wait_for_decision(payload, mode)
    if decision is not None:
        print(json.dumps(codex_output(decision), separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
