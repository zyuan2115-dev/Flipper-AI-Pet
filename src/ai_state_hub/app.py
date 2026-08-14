from __future__ import annotations

import argparse
import json
import platform
import queue
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import __version__
from .agents import install, list_agents, reconfigure_codex_approval
from .device import STATES, bridge_status, connect_bridge, send_state
from .effects import load_effects, save_effects
from .settings import load_settings, save_settings
from .usb import bind_computer, inspect as inspect_usb, install as install_usb


EVENTS: list[dict] = []
SUBSCRIBERS: list[queue.Queue] = []
CURRENT_STATE = "idle"
STATIC = Path(__file__).with_name("static")


def publish(agent: str, event: str, state: str) -> None:
    global CURRENT_STATE
    CURRENT_STATE = state
    item = {"time": time.strftime("%H:%M:%S"), "agent": agent, "event": event, "state": state}
    EVENTS.append(item)
    del EVENTS[:-100]
    for subscriber in list(SUBSCRIBERS):
        try: subscriber.put_nowait(item)
        except queue.Full: pass


def platforms() -> list[dict]:
    current = platform.system()
    return [
        {"name": "macOS", "current": current == "Darwin", "status": "可安装", "service": "LaunchAgent 用户服务", "package": ".app / .dmg"},
        {"name": "Windows", "current": current == "Windows", "status": "可安装", "service": "当前用户启动项", "package": "ARM64 EXE / ZIP"},
        {"name": "Linux", "current": current == "Linux", "status": "方案已定义", "service": "systemd --user", "package": ".deb / AppImage"},
    ]


class Handler(BaseHTTPRequestHandler):
    server_version = "AIStateHub/0.1"
    port = 7800

    def log_message(self, *_): pass

    def json(self, value: object, status: int = 200) -> None:
        raw = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def body(self) -> dict:
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            raw = (STATIC / "index.html").read_bytes(); self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
        elif path == "/api/status": self.json({"version": __version__, "platform": platform.system(), "current_state": CURRENT_STATE, "platforms": platforms()})
        elif path == "/api/agents": self.json({"agents": list_agents()})
        elif path == "/api/devices": self.json({"devices": [bridge_status()]})
        elif path == "/api/effects": self.json({"effects": load_effects()})
        elif path == "/api/settings": self.json({"settings": load_settings()})
        elif path == "/api/usb": self.json(inspect_usb())
        elif path == "/api/events/history": self.json({"events": EVENTS})
        elif path == "/api/events": self.stream_events()
        else: self.json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self.body()
            if path.startswith("/api/agents/") and path.endswith("/install"):
                self.json(install(path.split("/")[3], self.port))
            elif path == "/api/devices/flipper-zero/state":
                state = body.get("state", "")
                response = send_state(state); publish("manual", "state", state); self.json({"ok": True, "response": response})
            elif path == "/api/devices/flipper-zero/connect":
                self.json(connect_bridge())
            elif path == "/api/effects":
                self.json({"ok": True, "effects": save_effects(body.get("effects", {}))})
            elif path == "/api/settings":
                settings = save_settings(body.get("settings", {}))
                codex = next((agent for agent in list_agents() if agent["id"] == "codex"), None)
                hook = reconfigure_codex_approval() if codex and (codex["available"] or codex["installed"]) else None
                self.json({"ok": True, "settings": settings, "hook": hook})
            elif path == "/api/usb/install":
                result = install_usb(); publish("system", "usb_install", "idle"); self.json(result)
            elif path == "/api/usb/bind":
                self.json(bind_computer())
            elif path == "/api/hook":
                state = body.get("state", "idle")
                if state not in STATES: raise ValueError("无效状态")
                try: send_state(state)
                except (OSError, RuntimeError): pass
                publish(str(body.get("agent", "unknown")), str(body.get("event", "hook")), state)
                self.json({"ok": True})
            else: self.json({"error": "not found"}, 404)
        except (ValueError, OSError, RuntimeError, json.JSONDecodeError) as error:
            self.json({"error": str(error)}, 400)

    def stream_events(self) -> None:
        subscriber: queue.Queue = queue.Queue(50); SUBSCRIBERS.append(subscriber)
        self.send_response(200); self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache"); self.send_header("Connection", "keep-alive"); self.end_headers()
        try:
            while True:
                try: item = subscriber.get(timeout=15); data = json.dumps(item, ensure_ascii=False)
                except queue.Empty: data = json.dumps({"time": time.strftime("%H:%M:%S"), "event": "heartbeat"})
                self.wfile.write(f"data: {data}\n\n".encode()); self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError): pass
        finally: SUBSCRIBERS.remove(subscriber)


def main() -> None:
    parser = argparse.ArgumentParser(description="Flipper Pet local AI state hub")
    parser.add_argument("command", nargs="?", default="serve", choices=("serve",))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7800)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(); Handler.port = args.port
    print(f"Flipper Pet console: http://{args.host}:{args.port}")
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=(f"http://{args.host}:{args.port}",)).start()
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__": main()
