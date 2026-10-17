$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path -Path $DesktopPath -ChildPath "YouTube Downloader Ultra.lnk"

$ExePath = Join-Path -Path $PSScriptRoot -ChildPath "dist\YouTube_Downloader\YouTube_Downloader.exe"
$WorkingDir = Join-Path -Path $PSScriptRoot -ChildPath "dist\YouTube_Downloader"

if (-not (Test-Path $ExePath)) {
    Write-Error "Executable not found at: $ExePath"
    exit 1
}

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = $WorkingDir
$Shortcut.Description = "YouTube Ultra Downloader [Gothic Crimson Edition] - Silent yt-dlp GUI"
$Shortcut.IconLocation = "$ExePath,0"
$Shortcut.Save()

# Also create shortcut in main project folder
$FolderShortcutPath = Join-Path -Path $PSScriptRoot -ChildPath "YouTube Downloader Ultra.lnk"
$FolderShortcut = $WshShell.CreateShortcut($FolderShortcutPath)
$FolderShortcut.TargetPath = $ExePath
$FolderShortcut.WorkingDirectory = $WorkingDir
$FolderShortcut.Description = "YouTube Ultra Downloader [Gothic Crimson Edition] - Silent yt-dlp GUI"
$FolderShortcut.IconLocation = "$ExePath,0"
$FolderShortcut.Save()

Write-Host "Standalone EXE Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host "Target: $ExePath"
