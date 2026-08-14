# Flipper AI Pet

Flipper AI Pet connects Flipper Zero with desktop AI tools and shows AI activity through lights, sound, and screen prompts.

Flipper AI Pet 用于连接 Flipper Zero 与桌面 AI 工具，通过灯光、提示音和屏幕提示显示 AI 当前状态。

## Documentation

- Chinese install guide: [docs/INSTALL.zh-CN.md](docs/INSTALL.zh-CN.md)
- English guide: [docs/INSTALL.en.md](docs/INSTALL.en.md)
- Platform notes: [docs/platforms.md](docs/platforms.md)
- Flipper app notes: [flipper/README.md](flipper/README.md)

## What It Includes

- local Web console
- USB / USB-C install and update for the Flipper app
- BLE bridge with secure pairing
- approval takeover for Codex
- status hooks for Claude Code, Cursor, GitHub Copilot, and Qoder
- desktop packages and Flipper app binaries in this repository

## Downloads

- macOS package: [dist/Flipper-Pet-macOS-arm64.dmg](dist/Flipper-Pet-macOS-arm64.dmg)
- Windows x64 package: [dist/Flipper-Pet-Windows-x64.zip](dist/Flipper-Pet-Windows-x64.zip)
- Windows ARM64 package: [dist/Flipper-Pet-Windows-arm64.zip](dist/Flipper-Pet-Windows-arm64.zip)
- Flipper Zero app: [flipper/dist/ai_pet.fap](flipper/dist/ai_pet.fap)

Optional raw desktop binaries:

- macOS app bundle: [dist/Flipper Pet.app](dist/Flipper%20Pet.app)
- Windows x64 executable: [dist/FlipperPet-Windows-x64.exe](dist/FlipperPet-Windows-x64.exe)
- Windows ARM64 executable: [dist/FlipperPet.exe](dist/FlipperPet.exe)

## Windows Architecture

- Windows x64 is for mainstream Intel / AMD PCs.
- Windows ARM64 is for Windows on ARM devices.

## Quick Start

1. Install the desktop app for your operating system and processor architecture.
2. Connect Flipper Zero over USB-C and install `ai_pet.fap` from the local Web console.
3. Bind the computer once, then open `Apps -> Tools -> AI Pet` on the Flipper.
4. Open the local console at `http://127.0.0.1:8781/`.
5. Install the AI integration you want from the Web console.

## Current Tool Support

- Codex: status + approval takeover
- Claude Code: status hooks; direct approve / deny takeover is not implemented yet
- Cursor: status hooks
- GitHub Copilot: status hooks
- Qoder: status hooks

## Approval Modes

- Full takeover
- No takeover
- Handoff takeover with custom timeout

## Custom Effects

Each AI state can be customized from the desktop side with color, brightness, light behavior, auto-off timeout, and sound behavior.

These settings are stored on the computer and sent to the Flipper when state changes occur.

## Run From Source

```bash
PYTHONPATH=src python3 -m ai_state_hub.app serve --port 8781
```

Then open `http://127.0.0.1:8781/`.

## Build

- macOS: [packaging/build_macos.sh](packaging/build_macos.sh)
- Windows: [packaging/build_windows.ps1](packaging/build_windows.ps1)
- PyInstaller spec: [packaging/FlipperPet.spec](packaging/FlipperPet.spec)

## Gallery

<img width="2996" height="1594" alt="image" src="https://github.com/user-attachments/assets/88fa1ac7-469a-4ebe-a5c4-46472b4e2b12" />

<img width="3000" height="1550" alt="image" src="https://github.com/user-attachments/assets/16c28db2-1f58-4c70-ad22-c03d425c0555" />

<img width="1080" height="1920" alt="image" src="https://github.com/user-attachments/assets/82cc75ed-375a-482c-b3cb-40f288521666" />

<img width="1080" height="1920" alt="image" src="https://github.com/user-attachments/assets/bd544aac-fd19-46d5-a38c-d3dc69a26266" />

<img width="1080" height="1920" alt="image" src="https://github.com/user-attachments/assets/9c593eb5-2fef-49e8-a789-79f0c5355803" />

<img width="1080" height="1920" alt="image" src="https://github.com/user-attachments/assets/7f909e07-5e7e-4ad7-9253-46564db4afd8" />

<img width="596" height="792" alt="image" src="https://github.com/user-attachments/assets/ba47a471-0a14-4bab-9012-0e4def239894" />

## License

[Apache-2.0](LICENSE)
