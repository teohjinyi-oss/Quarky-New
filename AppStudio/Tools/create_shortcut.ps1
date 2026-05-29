$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$Desktop\Quarky_Ai.lnk")
$Shortcut.TargetPath = "C:\Users\User\OneDrive\LouisAi\QuarkyGUI.bat"
$Shortcut.WorkingDirectory = "C:\Users\User\OneDrive\LouisAi"
$Shortcut.WindowStyle = 7
$Shortcut.Description = "Quarky_Ai v2 — Desktop AI Assistant"
$Shortcut.Save()
Write-Host "Shortcut created at: $Desktop\Quarky_Ai.lnk"
