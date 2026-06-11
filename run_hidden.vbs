' Start run_local.ps1 volledig onzichtbaar (geen flikkerend venster).
' De "0" = verborgen venster, False = niet wachten.
CreateObject("WScript.Shell").Run _
  "powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""C:\Users\joris\Claude\scorito-wk2026-cloud\run_local.ps1""", _
  0, False
