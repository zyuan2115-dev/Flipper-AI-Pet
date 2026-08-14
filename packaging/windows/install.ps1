$ErrorActionPreference = "Stop"
$Port = if ($env:AI_STATE_HUB_PORT) { $env:AI_STATE_HUB_PORT } else { "7800" }
$InstallDir = Join-Path $env:LOCALAPPDATA "FlipperPet"
$SourceExe = Join-Path $PSScriptRoot "FlipperPet.exe"
$SourceBridge = Join-Path $PSScriptRoot "flipper-state.exe"
$Exe = Join-Path $InstallDir "FlipperPet.exe"
$Bridge = Join-Path $InstallDir "flipper-state.exe"
$RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"

if (-not (Test-Path $SourceExe)) {
  throw "FlipperPet.exe was not found next to install.ps1"
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Copy-Item -Path $SourceExe -Destination $Exe -Force
if (-not (Test-Path $SourceBridge)) { throw "flipper-state.exe was not found next to install.ps1" }
Copy-Item -Path $SourceBridge -Destination $Bridge -Force

$LaunchCommand = "`"$Exe`" serve --host 127.0.0.1 --port $Port"
if (-not (Test-Path $RunKey)) {
  New-Item -Path $RunKey | Out-Null
}
New-ItemProperty -Path $RunKey -Name "FlipperPet" -Value $LaunchCommand -PropertyType String -Force | Out-Null
New-ItemProperty -Path $RunKey -Name "FlipperPetBridge" -Value "`"$Bridge`" service" -PropertyType String -Force | Out-Null
Start-Process -FilePath $Exe -ArgumentList @("serve", "--host", "127.0.0.1", "--port", $Port)
Start-Process -FilePath $Bridge -ArgumentList @("service") -WindowStyle Hidden

Write-Host "Installed to $Exe"
Write-Host "Startup entry: HKCU\Software\Microsoft\Windows\CurrentVersion\Run\FlipperPet"
Write-Host "Console: http://127.0.0.1:$Port"
