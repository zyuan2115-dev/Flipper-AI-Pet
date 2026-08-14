param(
  [ValidateSet("x64", "arm64")]
  [string]$Arch
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $Arch) {
  if ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture -eq [System.Runtime.InteropServices.Architecture]::Arm64) {
    $Arch = "arm64"
  } else {
    $Arch = "x64"
  }
}

python -m pip install --upgrade pyinstaller pyserial "bleak>=1.0,<2"
python -m PyInstaller --clean --noconfirm --onefile --windowed --name "FlipperPet" --paths src `
  --add-data "src/ai_state_hub/static;ai_state_hub/static" `
  --add-data "flipper/dist/ai_pet.fap;flipper/dist" `
  --hidden-import serial --hidden-import serial.tools.list_ports packaging/main.py
python -m PyInstaller --clean --noconfirm --onefile --console --name "flipper-state" --paths "flipper/mac-client/src" packaging/bridge_main.py

$ZipName = "dist/Flipper-Pet-Windows-$Arch.zip"
Compress-Archive -Path "dist/FlipperPet.exe", "dist/flipper-state.exe", "packaging/windows/install.ps1" `
  -DestinationPath $ZipName -Force

Write-Host "$Root\\$ZipName"
