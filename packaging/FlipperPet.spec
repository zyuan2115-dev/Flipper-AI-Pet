# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH).parent
datas = [
    (str(root / "src" / "ai_state_hub" / "static"), "ai_state_hub/static"),
    (str(root / "flipper" / "dist" / "ai_pet.fap"), "flipper/dist"),
]

a = Analysis(
    [str(root / "src" / "ai_state_hub" / "app.py")],
    pathex=[str(root / "src")],
    binaries=[], datas=datas, hiddenimports=["serial", "serial.tools.list_ports", "ai_state_hub.flipper_storage"],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="Flipper Pet", debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          disable_windowed_traceback=False, argv_emulation=False,
          target_arch=None, codesign_identity=None, entitlements_file=None,
          icon=None)
