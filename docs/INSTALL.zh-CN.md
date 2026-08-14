# Flipper Pet 安装、部署与使用说明

## 1. 发布内容

本仓库已经包含可直接使用的发布产物：

- macOS：`dist/Flipper Pet.app`、`dist/Flipper-Pet-macOS-arm64.dmg`
* Windows x64（Intel / AMD）：`dist/FlipperPet-Windows-x64.exe`、`dist/Flipper-Pet-Windows-x64.zip`
* Windows ARM64：`dist/FlipperPet-Windows-arm64.exe`、`dist/Flipper-Pet-Windows-arm64.zip`
- Flipper 应用：`flipper/dist/ai_pet.fap`

## 2. 使用前准备

### Flipper Zero

- 已插入 microSD 卡
- 已开启蓝牙
- 建议使用官方固件新版 API 已验证环境

### macOS / Windows 电脑

- 蓝牙可用
- 首次安装 Flipper 应用时建议准备 USB-C 数据线

## 3. 桌面程序安装

### macOS

1. 打开 `dist/Flipper-Pet-macOS-arm64.dmg`
2. 将 `Flipper Pet.app` 拖入 `Applications`
3. 启动应用
4. 打开本地控制台：`http://127.0.0.1:7800/`

### Windows

大多数 Intel / AMD Windows 电脑请选择 Windows x64 包。Windows ARM64 包仅适用于 Windows on ARM 设备。

推荐优先使用一键安装 EXE：

1. Intel / AMD：直接运行 `dist/FlipperPet-Windows-x64.exe`
2. Windows on ARM：直接运行 `dist/FlipperPet-Windows-arm64.exe`

安装器会自动安装 Flipper Pet 控制台和 `flipper-state` BLE Bridge，并注册当前用户启动项。

如需手动安装或修复，也可以解压 ZIP 后运行 `install.ps1`。

启动后打开：`http://127.0.0.1:7800/`

## 4. 安装 Flipper AI Pet 应用

### 通过 Web 控制台安装

1. 用 USB-C 连接 Flipper Zero
2. 打开 `http://127.0.0.1:7800/`
3. 在 `USB / USB-C` 区域点击 `安装` 或 `更新`

程序会把 `flipper/dist/ai_pet.fap` 写入：

```text
/ext/apps/Tools/ai_pet.fap
```

## 5. 首次绑定电脑

1. 在 Web 控制台点击 `绑定电脑`
2. 这会生成电脑端密钥，并写入 Flipper：

```text
电脑：~/.flipper-pet/device.key
设备：/ext/apps_data/ai_pet/device.key
```

## 6. 启动 AI Pet 并建立 BLE 连接

1. 在 Flipper 打开：`Apps -> Tools -> AI Pet`
2. 桌面程序后台 Bridge 会自动扫描并连接
3. 首次连接成功后，AI Pet 会从等待界面进入待机状态

如果已连接但仍显示等待安全连接，请退出并重新打开 AI Pet，确保加载最新版本。

## 7. 接入 AI 工具

在 Web 控制台 `AI 接入` 区域点击对应 `安装`。

当前支持：

- Codex
- Claude Code
- Cursor
- GitHub Copilot
- Qoder

## 8. AI Pet 接管模式

在 Web 控制台可配置三种模式：

- `完全接管`：由 AI Pet 负责审批确认/取消
- `无需接管`：AI Pet 只提示待确认，电脑端操作
- `响应转移接管`：先由 AI Pet 响应，超时后转回电脑端

`响应转移接管` 支持自定义秒数，范围 `1-300` 秒。

## 9. 状态提醒自定义

可以为六种状态分别设置：

- 颜色
- 亮度
- 灯效模式
- 自动关闭秒数
- 蜂鸣方式

这些配置保存在电脑端，不写入 Flipper 固件。

## 10. 故障排查

### 7800 页面打不开

- 确认应用正在运行
- 确认 `http://127.0.0.1:7800/` 未被其他程序占用

### Flipper 一直显示等待安全连接

- 重新打开 AI Pet
- 确认已经点击过 `绑定电脑`
- 确认桌面程序蓝牙权限可用

### 电脑端可以确认，但 AI Pet 不接管

- 检查 Web 控制台里的接管模式
- 对 Codex 来说，新的权限请求会按当前模式生效
- Claude Code 当前仍以状态提示为主，不支持 Flipper 直接批准/拒绝

## 11. 从源码重新打包

### macOS

```bash
./packaging/build_macos.sh
```

### Windows

```powershell
./packaging/build_windows.ps1 -Arch x64
```
