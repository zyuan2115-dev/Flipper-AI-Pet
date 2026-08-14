# Flipper AI Pet App

This directory contains the Flipper Zero application source for AI Pet.

## License

This directory is licensed under [GPL-3.0](../LICENSE). The bundled Dolphin animation frames are derived from the official Flipper Zero firmware assets; see [NOTICE.md](NOTICE.md).

本目录采用 [GPL-3.0](../LICENSE) 授权。内置 Dolphin 动画帧来源于官方 Flipper Zero 固件资源，详见 [NOTICE.md](NOTICE.md)。

## Key Files

- [ai_state_display.c](ai_state_display.c)
- [ble_state_profile.c](ble_state_profile.c)
- [ai_pet_crypto.c](ai_pet_crypto.c)
- [application.fam](application.fam)

## Build

```bash
cd flipper
/Library/Frameworks/Python.framework/Versions/3.13/bin/ufbt
```

## Build and launch over USB

```bash
cd flipper
/Library/Frameworks/Python.framework/Versions/3.13/bin/ufbt launch
```

## Output

- release FAP: [dist/ai_pet.fap](dist/ai_pet.fap)
- debug ELF: [dist/debug/ai_pet_d.elf](dist/debug/ai_pet_d.elf)

## Notes

- The desktop Web console can install or update this FAP over USB.
- The app uses BLE plus an application-layer HMAC key for secure control.
- Sound now follows the Flipper system volume through NotificationApp instead of using a fixed HAL volume.
