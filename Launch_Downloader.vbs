Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

exePath = scriptDir & "\dist\YouTube_Downloader\YouTube_Downloader.exe"
If fso.FileExists(exePath) Then
    WshShell.Run """" & exePath & """", 0, False
Else
    localAppData = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
    pyExe = localAppData & "\Programs\Python\Python313\pythonw.exe"
    If Not fso.FileExists(pyExe) Then
        pyExe = "pythonw.exe"
    End If
    WshShell.Run """" & pyExe & """ """ & scriptDir & "\app.py""", 0, False
End If
