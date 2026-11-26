' Starts Edge Lab in the background (no window): pulls updates, then runs the server.
' Output goes to edge-lab.log in this folder (the pairing code is printed there too).
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run "cmd /c git pull > edge-lab.log 2>&1 & npm start >> edge-lab.log 2>&1", 0, False
