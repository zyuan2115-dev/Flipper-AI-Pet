from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
PORT = os.environ.get("AI_STATE_HUB_PORT", "7800")


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def message_box(text: str, title: str, flags: int = 0x40) -> None:
    ctypes.windll.user32.MessageBoxW(None, text, title, flags)


def install() -> tuple[Path, str]:
    import winreg

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not available")
    install_dir = Path(local_app_data) / "FlipperPet"
    install_dir.mkdir(parents=True, exist_ok=True)

    source_exe = resource_path("FlipperPet.exe")
    source_bridge = resource_path("flipper-state.exe")
    if not source_exe.is_file():
        raise RuntimeError("Installer payload is missing FlipperPet.exe")
    if not source_bridge.is_file():
        raise RuntimeError("Installer payload is missing flipper-state.exe")

    target_exe = install_dir / "FlipperPet.exe"
    target_bridge = install_dir / "flipper-state.exe"
    shutil.copy2(source_exe, target_exe)
    shutil.copy2(source_bridge, target_bridge)

    launch_command = f'"{target_exe}" serve --host 127.0.0.1 --port {PORT}'
    bridge_command = f'"{target_bridge}" service'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        winreg.SetValueEx(key, "FlipperPet", 0, winreg.REG_SZ, launch_command)
        winreg.SetValueEx(key, "FlipperPetBridge", 0, winreg.REG_SZ, bridge_command)

    creation_flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    bridge_flags = creation_flags | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen([str(target_exe), "serve", "--host", "127.0.0.1", "--port", PORT], creationflags=creation_flags)
    subprocess.Popen([str(target_bridge), "service"], creationflags=bridge_flags)
    return install_dir, PORT


def main() -> None:
    if os.name != "nt":
        raise SystemExit("This installer is for Windows only.")
    try:
        install_dir, port = install()
    except Exception as error:
        message_box(f"Flipper Pet 安装失败\n\n{error}", "Flipper Pet", 0x10)
        raise SystemExit(1)
    webbrowser.open(f"http://127.0.0.1:{port}/")
    message_box(
        f"Flipper Pet 已安装到\n{install_dir}\n\n控制台地址: http://127.0.0.1:{port}/",
        "Flipper Pet",
    )


if __name__ == "__main__":
    main()
