# Flipper Pet

Flipper Pet is a local AI status bridge for Flipper Zero. It includes:

- a local web console
- USB install and update for the Flipper app
- BLE bridge and secure pairing
- AI hooks for Codex and status hooks for Claude Code, Cursor, Copilot and Qoder
- packaged desktop builds in this repository

Flipper Pet 是一个本地 AI 状态桥接项目，面向 Flipper Zero。仓库同时包含：

- 本地 Web 管理控制台
- Flipper 应用的 USB 安装与更新
- BLE 桥接与安全绑定
- Codex 接管式审批 Hook，以及 Claude Code / Cursor / Copilot / Qoder 的状态 Hook
- 已编译好的桌面程序

## Release Assets

Prebuilt artifacts included in this repository:

- macOS app bundle: [dist/Flipper Pet.app](dist/Flipper%20Pet.app)
- macOS DMG: [dist/Flipper-Pet-macOS-arm64.dmg](dist/Flipper-Pet-macOS-arm64.dmg)
- Windows EXE: [dist/FlipperPet.exe](dist/FlipperPet.exe)
- Windows ZIP: [dist/Flipper-Pet-Windows-arm64.zip](dist/Flipper-Pet-Windows-arm64.zip)
- Flipper app (FAP): [flipper/dist/ai_pet.fap](flipper/dist/ai_pet.fap)

## Documentation

- 中文安装、部署与使用说明: [docs/INSTALL.zh-CN.md](docs/INSTALL.zh-CN.md)
- English installation, deployment and usage guide: [docs/INSTALL.en.md](docs/INSTALL.en.md)
- Cross-platform notes: [docs/platforms.md](docs/platforms.md)
- Flipper app development notes: [flipper/README.md](flipper/README.md)

## Repository Layout

```text
dist/                Desktop release artifacts
docs/                User-facing documentation
flipper/             Flipper Zero app source and built FAP
packaging/           Desktop packaging scripts
src/ai_state_hub/    Local web service, USB installer, BLE bridge logic
promlight_installer.py
pyproject.toml
```

## Quick Start

For users, start with the Chinese or English install guide above.

For developers, run the local console with:

```bash
PYTHONPATH=src python3 -m ai_state_hub.app serve --port 8781
```

Then open `http://127.0.0.1:8781/`.

## Packaging

- macOS build script: [packaging/build_macos.sh](packaging/build_macos.sh)
- Windows build script: [packaging/build_windows.ps1](packaging/build_windows.ps1)
- PyInstaller spec: [packaging/FlipperPet.spec](packaging/FlipperPet.spec)
