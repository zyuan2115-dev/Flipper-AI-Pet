#!/bin/sh
set -eu
PORT="${AI_STATE_HUB_PORT:-7800}"
BIN="$(command -v ai-state-hub)"
DIR="$HOME/.config/systemd/user"
DEST="$DIR/ai-state-hub.service"
mkdir -p "$DIR"
sed -e "s|@EXECUTABLE@|$BIN|g" -e "s|@PORT@|$PORT|g" \
  "$(dirname "$0")/ai-state-hub.service.in" > "$DEST"
systemctl --user daemon-reload
systemctl --user enable --now ai-state-hub.service
echo "Installed: http://127.0.0.1:$PORT"
