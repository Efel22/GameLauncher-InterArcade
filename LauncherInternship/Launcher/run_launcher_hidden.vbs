' Runs __start_launcher.bat with no visible console window - point Windows'
' Startup folder (or Task Scheduler) at THIS file, not at the .bat directly.
' Keep this file in the same folder as __start_launcher.bat; it finds it
' relative to itself, so the pair can be moved or copied to another machine
' together without editing anything.

Dim fso, scriptDir, batPath, objShell

Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = scriptDir & "\__start_launcher.bat"

Set objShell = CreateObject("WScript.Shell")
objShell.Run """" & batPath & """", 0, False