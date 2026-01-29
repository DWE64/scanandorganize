' BASIC Scanner - Lance la vérification sans afficher de fenêtre terminal
' Double-cliquez sur verify.vbs : la vérification s'exécute en arrière-plan, un message indique le résultat.

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
' 0 = fenêtre cachée, True = attendre la fin
code = sh.Run("powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & dir & "\verify.ps1""", 0, True)
If code = 0 Then
  MsgBox "Vérification terminée : succès.", vbInformation, "BASIC Scanner"
Else
  MsgBox "Vérification terminée : des erreurs ont été détectées (code " & code & "). Consultez verify.ps1 en ligne de commande pour les détails.", vbExclamation, "BASIC Scanner"
End If
