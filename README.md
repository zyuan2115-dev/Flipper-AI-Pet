# Flipper AI Pet

Flipper AI Pet connects Flipper Zero with desktop AI tools and shows AI activity through lights, sound, and screen prompts.

Flipper AI Pet 用于连接 Flipper Zero 与桌面 AI 工具，通过灯光、提示音和屏幕提示显示 AI 当前状态。

## Documentation / 文档

- 中文安装、部署与使用说明: [docs/INSTALL.zh-CN.md](docs/INSTALL.zh-CN.md)
- English installation, deployment, and usage guide: [docs/INSTALL.en.md](docs/INSTALL.en.md)
- Platform notes / 平台说明: [docs/platforms.md](docs/platforms.md)
- Flipper app notes / Flipper 应用说明: [flipper/README.md](flipper/README.md)

## What It Includes / 功能

- Local Web console / 本地 Web 管理控制台
- USB / USB-C install and update for the Flipper app / 通过 USB / USB-C 安装和更新 Flipper 应用
- BLE bridge with secure pairing / 具备安全配对的 BLE 桥接
- Codex approval takeover / Codex 审批接管
- Status hooks for Claude Code, Cursor, GitHub Copilot, and Qoder / Claude Code、Cursor、GitHub Copilot 和 Qoder 状态 Hook
- Desktop packages and Flipper app binaries / 桌面安装包和 Flipper 应用产物

## Downloads / 下载

- macOS ARM64 package / macOS ARM64 安装包: [dist/Flipper-Pet-macOS-arm64.dmg](dist/Flipper-Pet-macOS-arm64.dmg)
- Windows x64 package / Windows x64 安装包: [dist/Flipper-Pet-Windows-x64.zip](dist/Flipper-Pet-Windows-x64.zip)
- Windows ARM64 package / Windows ARM64 安装包: [dist/Flipper-Pet-Windows-arm64.zip](dist/Flipper-Pet-Windows-arm64.zip)
- Flipper Zero app / Flipper Zero 应用: [flipper/dist/ai_pet.fap](flipper/dist/ai_pet.fap)

Desktop installers / 桌面安装包:

- macOS app bundle: [dist/Flipper Pet.app](dist/Flipper%20Pet.app)
- Windows one-click installer: [dist/FlipperPet-Windows-x64.exe](dist/FlipperPet-Windows-x64.exe)
- Windows ZIP packages still include both the console and the required BLE Bridge for manual install or repair.

## Windows Architecture / Windows 架构选择

- Windows x64 is for mainstream Intel / AMD PCs. / Windows x64 适用于主流 Intel / AMD 电脑。
- Windows ARM64 is for Windows on ARM devices. / Windows ARM64 仅适用于 Windows on ARM 设备。

## Quick Start / 快速开始

1. Install the desktop app for your operating system and processor architecture. / 安装与你的操作系统和处理器架构对应的桌面程序。
2. Connect Flipper Zero over USB-C and install `ai_pet.fap` from the local Web console. / 用 USB-C 连接 Flipper Zero，在本地 Web 控制台安装 `ai_pet.fap`。
3. Bind the computer once, then open `Apps -> Tools -> AI Pet` on the Flipper. / 首次绑定电脑后，在 Flipper 打开 `Apps -> Tools -> AI Pet`。
4. Open the local console at `http://127.0.0.1:8781/`. / 打开本地控制台 `http://127.0.0.1:8781/`。
5. Install the AI integration you want from the Web console. / 在 Web 控制台安装所需 AI 工具的接入配置。

## Current Tool Support / 当前工具支持

- Codex: status + approval takeover / 状态显示 + 审批接管
- Claude Code: status hooks; direct approve / deny takeover is not implemented yet / 状态 Hook；暂未支持直接批准或拒绝接管
- Cursor: status hooks / 状态 Hook
- GitHub Copilot: status hooks / 状态 Hook
- Qoder: status hooks / 状态 Hook

## Approval Modes / 审批模式

- Full takeover / 完全接管
- No takeover / 无需接管
- Handoff takeover with custom timeout / 自定义超时的响应转移接管

## Custom Effects / 自定义提醒

Each AI state can be customized from the desktop side with color, brightness, light behavior, auto-off timeout, and sound behavior.

每种 AI 状态均可在电脑端自定义颜色、亮度、灯效模式、自动关闭时间和提示音方式。设置保存在电脑端，在状态变化时发送给 Flipper。

## Run From Source / 从源码运行

```bash
PYTHONPATH=src python3 -m ai_state_hub.app serve --port 8781
```

Then open `http://127.0.0.1:8781/`. / 然后打开 `http://127.0.0.1:8781/`。

## Build / 打包

- macOS: [packaging/build_macos.sh](packaging/build_macos.sh)
- Windows: [packaging/build_windows.ps1](packaging/build_windows.ps1)
- PyInstaller spec / PyInstaller 配置: [packaging/FlipperPet.spec](packaging/FlipperPet.spec)

## Gallery / 截图

<img width="2996" height="1594" alt="Web console" src="https://github.com/user-attachments/assets/88fa1ac7-469a-4ebe-a5c4-46472b4e2b12" />

<img width="3000" height="1550" alt="Web console settings" src="https://github.com/user-attachments/assets/16c28db2-1f58-4c70-ad22-c03d425c0555" />

<img width="1080" height="1920" alt="Flipper AI Pet screen" src="https://github.com/user-attachments/assets/82cc75ed-375a-482c-b3cb-40f288521666" />

<img width="1080" height="1920" alt="Flipper AI Pet screen" src="https://github.com/user-attachments/assets/bd544aac-fd19-46d5-a38c-d3dc69a26266" />

<img width="1080" height="1920" alt="Flipper AI Pet screen" src="https://github.com/user-attachments/assets/9c593eb5-2fef-49e8-a789-79f0c5355803" />

<img width="1080" height="1920" alt="Flipper AI Pet screen" src="https://github.com/user-attachments/assets/7f909e07-5e7e-4ad7-9253-46564db4afd8" />

<img width="596" height="792" alt="Flipper AI Pet screen" src="https://github.com/user-attachments/assets/ba47a471-0a14-4bab-9012-0e4def239894" />

## License / 许可证

This repository is licensed under [GNU General Public License v3.0](LICENSE).

The bundled Dolphin animation assets are derived from the official Flipper Zero firmware; see [flipper/NOTICE.md](flipper/NOTICE.md) for source and attribution.

本仓库统一采用 [GNU General Public License v3.0](LICENSE) 授权。

内置 Dolphin 动画资源来源于官方 Flipper Zero 固件，来源与署名详见 [flipper/NOTICE.md](flipper/NOTICE.md)。

## Acknowledgements / 致谢

Thanks to [Sch-ray/AI_State_Display](https://github.com/Sch-ray/AI_State_Display) for project ideas and inspiration.

感谢 [Sch-ray/AI_State_Display](https://github.com/Sch-ray/AI_State_Display) 项目提供思路参考。
