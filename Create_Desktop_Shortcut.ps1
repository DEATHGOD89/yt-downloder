$WshShell = New-Object -ComObject WScript.Shell

$ExePath = Join-Path -Path $PSScriptRoot -ChildPath "dist\YouTube_Downloader\YouTube_Downloader.exe"
$WorkingDir = Join-Path -Path $PSScriptRoot -ChildPath "dist\YouTube_Downloader"
$IconFile = Join-Path -Path $PSScriptRoot -ChildPath "assets\app_icon.ico"

if (Test-Path $ExePath) {
    $Target = $ExePath
    $TargetDir = $WorkingDir
    $IconLoc = "$ExePath,0"
} else {
    $VbsPath = Join-Path -Path $PSScriptRoot -ChildPath "Launch_Downloader.vbs"
    if (Test-Path $VbsPath) {
        $Target = $VbsPath
        $TargetDir = $PSScriptRoot
        $IconLoc = $IconFile
    } else {
        $Target = Join-Path -Path $PSScriptRoot -ChildPath "Launch_Downloader.bat"
        $TargetDir = $PSScriptRoot
        $IconLoc = $IconFile
    }
}

$ShortcutLocations = @(
    (Join-Path -Path ([Environment]::GetFolderPath("Desktop")) -ChildPath "YouTube Downloader Ultra.lnk"),
    (Join-Path -Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs" -ChildPath "YouTube Downloader Ultra.lnk"),
    (Join-Path -Path $PSScriptRoot -ChildPath "YouTube Downloader Ultra.lnk")
)

foreach ($scPath in $ShortcutLocations) {
    try {
        $parentDir = Split-Path -Path $scPath -Parent
        if (-not (Test-Path $parentDir)) {
            New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
        }
        $sc = $WshShell.CreateShortcut($scPath)
        $sc.TargetPath = $Target
        $sc.WorkingDirectory = $TargetDir
        $sc.Description = "YouTube Ultra Downloader [Gothic Crimson Edition] - Silent yt-dlp GUI"
        if (Test-Path $IconFile) {
            $sc.IconLocation = if ($IconLoc) { $IconLoc } else { "$IconFile,0" }
        }
        $sc.Save()
        Write-Host "Created shortcut: $scPath" -ForegroundColor Green
    } catch {
        Write-Warning "Could not update shortcut at: $scPath ($($_.Exception.Message))"
    }
}

# Flush Windows Shell icon cache so icons refresh immediately without rebooting
try {
    Add-Type -TypeDefinition @"
    using System;
    using System.Runtime.InteropServices;
    public class ShellNotify {
        [DllImport("shell32.dll")]
        public static extern void SHChangeNotify(int wEventId, int uFlags, IntPtr dwItem1, IntPtr dwItem2);
    }
"@
    [ShellNotify]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
    Write-Host "Windows Shell icon cache refreshed successfully!" -ForegroundColor Cyan
} catch {
    # Non-critical fallback
}
