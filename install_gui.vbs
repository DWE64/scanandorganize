' BASIC Scanner - Lance l'installateur sans afficher de fenêtre terminal
' Double-cliquez sur install_gui.vbs pour ouvrir uniquement la fenêtre d'installation.

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
' Utiliser pythonw du PATH (pas du venv) pour que le premier lancement fonctionne avant installation
sh.Run "pythonw """ & dir & "\install_gui.py""", 1, False
