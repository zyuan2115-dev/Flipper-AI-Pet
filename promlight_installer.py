#!/usr/bin/env python3
"""PromLight-style local AI hook installer.

Run with ``python3 promlight_installer.py`` and open http://127.0.0.1:7800.
Only the standard library is required.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST, PORT = "127.0.0.1", int(os.getenv("PROMLIGHT_PORT", "7800"))
HOME = Path(os.getenv("FLIPPER_INSTALL_HOME", str(Path.home()))).expanduser()
HOOK = "python3 -c \"import urllib.request,json; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:{port}/api/hook', data=json.dumps({{'agent':'{agent}','event':'{event}'}}).encode(), headers={{'Content-Type':'application/json'}}), timeout=1)\""

AGENTS = {
    "claude": {"app": "Claude Code", "config": HOME / ".claude" / "settings.json", "commands": ["claude"]},
    "codex": {"app": "Codex", "config": HOME / ".codex" / "hooks.json", "commands": ["codex"]},
    "cursor": {"app": "Cursor", "config": HOME / ".cursor" / "hooks.json", "commands": ["cursor"]},
    "copilot": {"app": "GitHub Copilot", "config": HOME / ".copilot" / "hooks.json", "commands": ["gh", "copilot"]},
    "qoder": {"app": "Qoder", "config": HOME / ".qoder" / "hooks.json", "commands": ["qoder"]},
}

INDEX = """<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>PromLight AI 一键安装</title><style>
body{font:15px system-ui,-apple-system,sans-serif;background:#f3f5f9;color:#273142;max-width:820px;margin:40px auto;padding:0 18px}main{background:white;border:1px solid #dde3ec;border-radius:12px;padding:26px;box-shadow:0 4px 20px #18243a12}h1{margin-top:0;color:#d76d31}p{color:#67748c}.agent{display:flex;align-items:center;justify-content:space-between;padding:13px 0;border-bottom:1px solid #edf0f4}.agent small{display:block;color:#8893a5}.state{color:#16a34a}.state.off{color:#d97706}button{border:1px solid #e07a3f;background:#fff7f0;color:#b35c25;border-radius:7px;padding:7px 13px;cursor:pointer}button.primary{background:#e07a3f;color:white;margin-right:8px}button:disabled{opacity:.5}#log{white-space:pre-wrap;background:#f8fafc;border:1px solid #e5eaf1;border-radius:8px;padding:12px;margin-top:22px;min-height:50px;font:13px ui-monospace,monospace}</style>
<main><h1>PromLight AI 一键安装</h1><p>检测本机支持 Hook 的 AI 工具，并把 PromLight 状态 Hook 安装到用户配置中。</p><div><button class='primary' onclick='install("all")'>一键安装全部</button><button onclick='refresh()'>重新检测</button></div><section id='agents'></section><div id='log'>准备就绪。</div></main>
<script>const $=s=>document.querySelector(s);async function api(u,o){let r=await fetch(u,{method:o?'POST':'GET',headers:{'Content-Type':'application/json'},body:o?JSON.stringify(o):undefined});return r.json()}async function refresh(){let d=await api('/api/agents');$('#agents').innerHTML=d.agents.map(a=>`<div class=agent><span><b>${a.app}</b><small>${a.config}</small></span><span class='state ${a.installed?'':'off'}'>${a.installed?'已安装':'未安装'} <button onclick="install('${a.name}')">${a.installed?'重新安装':'安装'}</button></span></div>`).join('')}async function install(n){document.querySelectorAll('button').forEach(b=>b.disabled=true);$('#log').textContent='正在安装 '+n+' ...';let d=await api('/api/setup',{agent:n});$('#log').textContent=(d.lines||[]).join('\\n')+(d.error?'\\n错误: '+d.error:'');await refresh();document.querySelectorAll('button').forEach(b=>b.disabled=false)}refresh()</script>"""

def available(name: str) -> bool:
    return os.getenv("FLIPPER_INSTALL_ALL") == "1" or any(shutil.which(c) for c in AGENTS[name]["commands"])

def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}

def install_agent(name: str) -> list[str]:
    spec = AGENTS[name]; path = spec["config"]; path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(path.name + ".promlight-backup-" + time.strftime("%Y%m%d%H%M%S"))
        shutil.copy2(path, backup)
    data = load_json(path)
    hooks = data.setdefault("hooks", {})
    if name in ("claude", "codex"):
        for event in ("SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "PermissionRequest", "Stop", "SessionEnd"):
            command = HOOK.format(agent=name, event=event, port=PORT)
            entries = hooks.setdefault(event, [])
            entries[:] = [item for item in entries if "127.0.0.1:7800/api/hook" not in json.dumps(item)]
            item = {"hooks": [{"type": "command", "command": command}]}
            if event in ("PreToolUse", "PostToolUse", "PermissionRequest"): item["matcher"] = ".*" if name == "codex" else "*"
            entries.append(item)
    else:
        events = ("sessionStart", "beforeSubmitPrompt", "postToolUse", "stop", "sessionEnd")
        for event in events:
            command = HOOK.format(agent=name, event=event, port=PORT)
            entries = hooks.setdefault(event, [])
            entries[:] = [item for item in entries if "127.0.0.1:7800/api/hook" not in json.dumps(item)]
            entries.append({"command": command})
        data.setdefault("version", 1)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return [f"[ok] {spec['app']}: 已写入 {path}", "      已创建备份（如原配置存在）"]

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def send_json(self, value, status=200):
        raw = json.dumps(value, ensure_ascii=False).encode(); self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path == "/":
            raw = INDEX.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
        elif self.path == "/api/agents":
            self.send_json({"agents": [{"name": n, "app": s["app"], "config": str(s["config"]), "available": available(n), "installed": s["config"].exists() and "/api/hook" in s["config"].read_text(errors="ignore")} for n, s in AGENTS.items()]})
        else: self.send_json({"error": "not found"}, 404)
    def do_POST(self):
        try: body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except json.JSONDecodeError: return self.send_json({"error": "invalid json"}, 400)
        if self.path == "/api/setup":
            target = body.get("agent", "all"); names = list(AGENTS) if target == "all" else [target]
            if any(n not in AGENTS for n in names): return self.send_json({"error": "unsupported agent"}, 400)
            lines = []
            for n in names:
                if not available(n): lines.append(f"[skip] {AGENTS[n]['app']}: 未检测到命令行程序"); continue
                lines.extend(install_agent(n))
            return self.send_json({"ok": True, "lines": lines})
        if self.path == "/api/hook": return self.send_json({"ok": True})
        self.send_json({"error": "not found"}, 404)

if __name__ == "__main__":
    print(f"PromLight AI installer: http://{HOST}:{PORT}"); ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
