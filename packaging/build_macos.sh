#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 -m PyInstaller --clean --noconfirm --onefile --windowed --name "Flipper Pet" --paths src \
  --add-data "src/ai_state_hub/static:ai_state_hub/static" \
  --add-data "flipper/dist/ai_pet.fap:flipper/dist" \
  --hidden-import serial --hidden-import serial.tools.list_ports packaging/main.py
STAGE="$ROOT/build/macos-dmg"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$ROOT/dist/Flipper Pet.app" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
hdiutil create -volname "Flipper Pet" -srcfolder "$STAGE" -ov -format UDZO "$ROOT/dist/Flipper-Pet-macOS-arm64.dmg"
echo "$ROOT/dist/Flipper-Pet-macOS-arm64.dmg"
