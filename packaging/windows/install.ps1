$ErrorActionPreference = "Stop"
$Port = if ($env:AI_STATE_HUB_PORT) { $env:AI_STATE_HUB_PORT } else { "7800" }
$InstallDir = Join-Path $env:LOCALAPPDATA "FlipperPet"
$SourceExe = Join-Path $PSScriptRoot "FlipperPet.exe"
$Exe = Join-Path $InstallDir "FlipperPet.exe"
$RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"

if (-not (Test-Path $SourceExe)) {
  throw "FlipperPet.exe was not found next to install.ps1"
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Copy-Item -Path $SourceExe -Destination $Exe -Force

$LaunchCommand = "`"$Exe`" serve --host 127.0.0.1 --port $Port"
New-Item -Path $RunKey -Force | Out-Null
New-ItemProperty -Path $RunKey -Name "FlipperPet" -Value $LaunchCommand -PropertyType String -Force | Out-Null
Start-Process -FilePath $Exe -ArgumentList @("serve", "--host", "127.0.0.1", "--port", $Port)

Write-Host "Installed to $Exe"
Write-Host "Startup entry: HKCU\Software\Microsoft\Windows\CurrentVersion\Run\FlipperPet"
Write-Host "Console: http://127.0.0.1:$Port"
