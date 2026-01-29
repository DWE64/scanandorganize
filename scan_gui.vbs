' BASIC Scanner - Lance l'interface sans afficher de fenêtre terminal
' Double-cliquez sur scan_gui.vbs pour ouvrir uniquement la fenêtre de l'application.

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = dir & "\.venv\Scripts\pythonw.exe"
If fso.FileExists(pythonw) Then
  sh.Run """" & pythonw & """ """ & dir & "\scan_gui.py""", 0, False
Else
  sh.Run "pythonw """ & dir & "\scan_gui.py""", 0, False
End If
