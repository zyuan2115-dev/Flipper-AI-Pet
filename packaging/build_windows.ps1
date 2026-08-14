$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
python -m pip install --upgrade pyinstaller pyserial
python -m PyInstaller --clean --noconfirm --onefile --windowed --name "FlipperPet" --paths src `
  --add-data "src/ai_state_hub/static;ai_state_hub/static" `
  --add-data "flipper/dist/ai_pet.fap;flipper/dist" `
  --hidden-import serial --hidden-import serial.tools.list_ports packaging/main.py
Compress-Archive -Path "dist/FlipperPet.exe", "packaging/windows/install.ps1" `
  -DestinationPath "dist/Flipper-Pet-Windows-arm64.zip" -Force
Write-Host "$Root\dist\Flipper-Pet-Windows-arm64.zip"
