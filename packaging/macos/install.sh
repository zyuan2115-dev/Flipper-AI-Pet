#!/bin/sh
set -eu
PORT="${AI_STATE_HUB_PORT:-7800}"
BIN="$(command -v ai-state-hub)"
DEST="$HOME/Library/LaunchAgents/com.flipperpet.ai-state-hub.plist"
LOG_DIR="$HOME/Library/Logs/FlipperPet"
mkdir -p "$LOG_DIR" "$(dirname "$DEST")"
sed -e "s|@EXECUTABLE@|$BIN|g" -e "s|@PORT@|$PORT|g" -e "s|@LOG_DIR@|$LOG_DIR|g" \
  "$(dirname "$0")/com.flipperpet.ai-state-hub.plist.in" > "$DEST"
launchctl bootout "gui/$(id -u)" "$DEST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$DEST"
echo "Installed: http://127.0.0.1:$PORT"
