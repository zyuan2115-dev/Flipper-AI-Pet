from __future__ import annotations

import glob
import hashlib
import os
import secrets
import sys
import threading
import time
from pathlib import Path


DEVICE_FAP = "/ext/apps/Tools/ai_pet.fap"
DEVICE_KEY = "/ext/apps_data/ai_pet/device.key"
LEGACY_DEVICE_FAP = "/ext/apps/Tools/ai_state_display.fap"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
LOCAL_FAP = BUNDLE_ROOT / "flipper" / "dist" / "ai_pet.fap"
USB_LOCK = threading.Lock()
USB_CACHE_SECONDS = 10
USB_CACHE: tuple[float, dict] | None = None
LOCAL_KEY = Path(os.getenv("AI_PET_KEY_FILE", "~/.flipper-pet/device.key")).expanduser()


def _ports() -> list[str]:
    if os.name == "nt":
        try:
            from serial.tools import list_ports
            matches = []
            for port in list_ports.comports():
                description = " ".join(
                    value or ""
                    for value in (port.description, port.manufacturer, port.product, port.hwid)
                ).lower()
                flipper_usb_id = port.vid == 0x0483 and port.pid == 0x5740
                if "flipper" in description or flipper_usb_id or "0483:5740" in description:
                    matches.append(port.device)
            return sorted(set(matches))
        except ImportError:
            return []
    patterns = ("/dev/cu.usbmodemflip_*", "/dev/ttyACM*")
    return sorted({path for pattern in patterns for path in glob.glob(pattern)})


def _storage_class():
    from .flipper_storage import FlipperStorage, FlipperStorageOperations
    return FlipperStorage, FlipperStorageOperations


def _inspect_unlocked() -> dict:
    ports = _ports()
    result = {
        "connected": bool(ports), "ports": ports, "port": ports[0] if ports else None,
        "installed": False, "local_ready": LOCAL_FAP.is_file(),
        "local_fap": str(LOCAL_FAP), "device_fap": DEVICE_FAP, "error": None,
    }
    if not ports:
        return result
    try:
        storage_class, _ = _storage_class()
        with storage_class(ports[0]) as storage:
            result["installed"] = storage.exist_file(DEVICE_FAP)
            if result["installed"]:
                result["device_size"] = storage.size(DEVICE_FAP)
        if LOCAL_FAP.exists():
            result["local_size"] = LOCAL_FAP.stat().st_size
            result["update_available"] = result.get("device_size") != result["local_size"]
    except Exception as error:
        result["error"] = str(error)
    return result


def inspect(force: bool = False) -> dict:
    global USB_CACHE
    if not force and USB_CACHE and time.monotonic() - USB_CACHE[0] < USB_CACHE_SECONDS:
        return dict(USB_CACHE[1])
    if not USB_LOCK.acquire(blocking=False):
        return {
            "connected": bool(_ports()), "ports": _ports(), "port": None,
            "installed": False, "local_ready": LOCAL_FAP.is_file(),
            "local_fap": str(LOCAL_FAP), "device_fap": DEVICE_FAP,
            "busy": True, "error": None,
        }
    try:
        result = _inspect_unlocked()
        USB_CACHE = (time.monotonic(), dict(result))
        return result
    finally:
        USB_LOCK.release()


def install() -> dict:
    global USB_CACHE
    with USB_LOCK:
        status = _inspect_unlocked()
        if not status["connected"]:
            raise RuntimeError("未检测到 USB/USB-C 连接的 Flipper")
        if not LOCAL_FAP.is_file():
            raise RuntimeError("项目内没有已编译的 AI Pet FAP")
        storage_class, operations_class = _storage_class()
        try:
            with storage_class(status["port"]) as storage:
                operations_class(storage).recursive_send(DEVICE_FAP, str(LOCAL_FAP), True)
                device_size = storage.size(DEVICE_FAP)
                local_size = LOCAL_FAP.stat().st_size
                device_md5 = storage.hash_flipper(DEVICE_FAP)
                local_md5 = hashlib.md5(LOCAL_FAP.read_bytes()).hexdigest()
                if device_size != local_size or device_md5 != local_md5:
                    raise RuntimeError(
                        f"写入校验失败: 设备 {device_size} bytes，本地 {local_size} bytes"
                    )
                if storage.exist_file(LEGACY_DEVICE_FAP):
                    storage.remove(LEGACY_DEVICE_FAP)
        except Exception as error:
            raise RuntimeError(f"安装失败: {error}") from error
        result = {
            "ok": True, "port": status["port"], "installed": True,
            "device_size": device_size, "md5": device_md5,
        }
        USB_CACHE = (time.monotonic(), {
            **status, "installed": True, "device_size": device_size,
            "local_size": local_size, "update_available": False, "error": None,
        })
        return result


def bind_computer() -> dict:
    global USB_CACHE
    with USB_LOCK:
        ports = _ports()
        if not ports:
            raise RuntimeError("未检测到 USB/USB-C 连接的 Flipper")
        LOCAL_KEY.parent.mkdir(parents=True, exist_ok=True)
        key = secrets.token_bytes(32)
        temp = LOCAL_KEY.with_suffix(".tmp")
        temp.write_bytes(key)
        os.chmod(temp, 0o600)
        os.replace(temp, LOCAL_KEY)
        storage_class, operations_class = _storage_class()
        try:
            with storage_class(ports[0]) as storage:
                operations_class(storage).recursive_send(DEVICE_KEY, str(LOCAL_KEY), True)
        except Exception as error:
            raise RuntimeError(f"绑定失败: {error}") from error
        USB_CACHE = None
        return {"ok": True, "port": ports[0], "bound": True, "key_file": str(LOCAL_KEY)}
