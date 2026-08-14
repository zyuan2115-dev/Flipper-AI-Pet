from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .effects import STATES, command_for

SOCKET = Path(os.getenv("FLIPPER_STATE_SOCKET", "/tmp/flipper-state.sock"))
TCP_HOST = os.getenv("FLIPPER_STATE_HOST", "127.0.0.1")
TCP_PORT = int(os.getenv("FLIPPER_STATE_PORT", "39871"))


def bridge_status() -> dict:
    return {
        "id": "flipper-zero",
        "name": "Flipper Zero",
        "type": "ble",
        "connected": _bridge_available(),
        "bridge": f"{TCP_HOST}:{TCP_PORT}" if os.name == "nt" else str(SOCKET),
        "states": list(STATES),
    }


async def _send(state: str) -> str:
    if os.name == "nt":
        reader, writer = await asyncio.wait_for(asyncio.open_connection(TCP_HOST, TCP_PORT), 1.5)
    else:
        reader, writer = await asyncio.wait_for(asyncio.open_unix_connection(SOCKET), 1.5)
    writer.write(f"{state}\n".encode())
    await writer.drain()
    response = (await asyncio.wait_for(reader.readline(), 3)).decode().strip()
    writer.close()
    await writer.wait_closed()
    if not response.startswith("ok:"):
        raise RuntimeError(response or "BLE bridge 未返回结果")
    return response


def send_state(state: str) -> str:
    if state not in STATES:
        raise ValueError("无效状态")
    if not _bridge_available():
        raise RuntimeError("Flipper BLE bridge 未运行")
    return asyncio.run(_send(command_for(state)))


def connect_bridge() -> dict:
    if _bridge_available():
        return {"ok": True, "connected": True, "message": "Bridge 已连接"}
    executable = shutil.which("flipper-state")
    if not executable:
        candidates = []
        if os.name == "nt":
            candidates.extend([
                Path(os.environ.get("LOCALAPPDATA", "")) / "FlipperPet" / "flipper-state.exe",
                Path(sys.executable).with_name("flipper-state.exe"),
            ])
        candidates.extend(sorted((Path.home() / "Library/Application Support/FlipperAIState").glob(".venv/bin/flipper-state")))
        executable = str(candidates[0]) if candidates else None
        executable = next((str(path) for path in candidates if path.is_file()), None)
    if not executable:
        raise RuntimeError("未找到 flipper-state Bridge，请先安装电脑端组件")
    subprocess.Popen(
        [executable, "service"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {"ok": True, "connected": False, "message": "正在扫描并连接 AI Pet；当前连接无需配对码"}


def _bridge_available() -> bool:
    if os.name != "nt":
        return SOCKET.exists()
    import socket
    try:
        with socket.create_connection((TCP_HOST, TCP_PORT), timeout=0.2):
            return True
    except OSError:
        return False
