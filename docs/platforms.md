# 跨平台交付方案

核心服务、管理页面和 Hook 协议保持一致，只替换后台服务、BLE 后端和安装包。

| 平台 | 后台运行 | BLE | 发布格式 | 当前状态 |
| --- | --- | --- | --- | --- |
| macOS 13+ | LaunchAgent | Bleak/CoreBluetooth | `.app` + 签名 `.dmg` | 开发闭环已可运行 |
| Windows 10/11 | 用户计划任务 | Bleak/WinRT | 签名 `.exe` 或 `.msi` | 服务脚本已提供，待真机验证 |
| Linux | systemd user | Bleak/BlueZ D-Bus | `.deb` + AppImage | 服务脚本已提供，待真机验证 |

## 统一要求

- Web 只监听 `127.0.0.1`，默认端口 `7800`。
- 正式包使用 PyInstaller 生成独立可执行文件，用户无需安装 Python。
- Hook 始终指向固定安装路径，升级时不得改变路径。
- 配置保存在用户目录，卸载默认保留配置和备份。
- 三个平台必须在原生 CI runner 构建；BLE 后端不能交叉编译验证。

## macOS

- 安装路径建议 `/Applications/Flipper Pet.app` 或 `~/Applications/Flipper Pet.app`。
- 首次启动请求蓝牙权限，并安装用户级 LaunchAgent。
- `.app`、内置 Python runtime 和 `.dmg` 均需 Developer ID 签名及 notarization。

## Windows

- 安装路径建议 `%LOCALAPPDATA%\FlipperPet\`，避免管理员权限。
- 用户登录时通过计划任务启动；不使用 Windows Service，BLE 权限更符合交互用户会话。
- 使用 PyInstaller + WiX/Inno Setup，最终 EXE/MSI 需要代码签名。

## Linux

- 后台使用 `systemd --user`，依赖 BlueZ 与 D-Bus。
- 安装器需要检查 `bluetoothctl show` 和用户会话总线。
- 桌面系统提供 `.deb`；通用分发可提供 AppImage。
