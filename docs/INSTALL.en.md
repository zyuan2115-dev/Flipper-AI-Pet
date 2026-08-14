# Flipper Pet Installation, Deployment, and Usage Guide

## 1. Included Release Assets

This repository already includes ready-to-use artifacts:

- macOS: `dist/Flipper Pet.app`, `dist/Flipper-Pet-macOS-arm64.dmg`
- Windows: `dist/FlipperPet.exe`, `dist/Flipper-Pet-Windows-arm64.zip`
- Flipper app: `flipper/dist/ai_pet.fap`

## 2. Requirements

### Flipper Zero

- microSD card inserted
- Bluetooth enabled
- official firmware environment recommended

### macOS / Windows computer

- Bluetooth available
- USB-C cable recommended for first-time app install

## 3. Install the Desktop App

### macOS

1. Open `dist/Flipper-Pet-macOS-arm64.dmg`
2. Drag `Flipper Pet.app` into `Applications`
3. Launch the app
4. Open the local console at `http://127.0.0.1:8781/`

### Windows

Either:

1. run `dist/FlipperPet.exe`, or
2. extract `dist/Flipper-Pet-Windows-arm64.zip` and run the packaged program

Then open `http://127.0.0.1:8781/`.

## 4. Install the Flipper AI Pet App

### Install from the Web Console

1. Connect Flipper Zero over USB-C
2. Open `http://127.0.0.1:8781/`
3. In the `USB / USB-C` section, click `Install` or `Update`

The app is written to:

```text
/ext/apps/Tools/ai_pet.fap
```

## 5. Bind the Computer

1. Click `Bind Computer` in the Web console
2. This creates a local key and writes the same key to the Flipper:

```text
Computer: ~/.flipper-pet/device.key
Device:   /ext/apps_data/ai_pet/device.key
```

## 6. Start AI Pet and Connect over BLE

1. On Flipper, open `Apps -> Tools -> AI Pet`
2. The desktop BLE bridge will scan and connect automatically
3. After successful secure authentication, AI Pet should move to idle

If the device still shows `Waiting for secure link`, exit and reopen AI Pet to ensure the latest version is loaded.

## 7. Connect AI Tools

Use the `AI Integration` section in the Web console and click `Install` for the tool you want.

Supported today:

- Codex
- Claude Code
- Cursor
- GitHub Copilot
- Qoder

## 8. AI Pet Takeover Modes

The Web console supports three approval modes:

- `Full takeover`: AI Pet handles approve / deny
- `No takeover`: AI Pet shows pending status, but approval stays on the computer
- `Handoff takeover`: AI Pet gets the first chance, then control returns to the computer after a timeout

`Handoff takeover` supports a custom timeout from `1` to `300` seconds.

## 9. Custom Status Effects

Each of the six states can be customized with:

- color
- brightness
- light behavior
- auto-off timeout
- sound style

These settings are stored on the computer, not inside the Flipper firmware.

## 10. Troubleshooting

### `8781` cannot be opened

- make sure the app is running
- make sure no other process is occupying `127.0.0.1:8781`

### AI Pet stays on `Waiting for secure link`

- reopen AI Pet on the Flipper
- make sure `Bind Computer` has already been completed
- make sure desktop Bluetooth permissions are granted

### Computer approval works but AI Pet does not take over

- verify the selected takeover mode in the Web console
- for Codex, new permission requests follow the current mode
- for Claude Code, status indication works, but direct approve / deny takeover is not implemented yet

## 11. Build from Source

### macOS

```bash
./packaging/build_macos.sh
```

### Windows

```powershell
./packaging/build_windows.ps1
```
