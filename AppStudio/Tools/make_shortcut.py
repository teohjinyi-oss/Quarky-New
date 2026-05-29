"""Create a desktop shortcut for Quarky_Ai v2."""
import os
import pathlib

desktop = pathlib.Path.home() / "Desktop"
bat_path = r"C:\Users\User\OneDrive\LouisAi\QuarkyGUI.bat"
work_dir = r"C:\Users\User\OneDrive\LouisAi"
shortcut_path = str(desktop / "Quarky_Ai.lnk")

vbs_content = f'''Set oWS = WScript.CreateObject("WScript.Shell")
Set oLink = oWS.CreateShortcut("{shortcut_path}")
oLink.TargetPath = "{bat_path}"
oLink.WorkingDirectory = "{work_dir}"
oLink.WindowStyle = 7
oLink.Description = "Quarky_Ai v2 — Desktop AI Assistant"
oLink.Save
'''

vbs_path = desktop / "_temp_shortcut.vbs"
vbs_path.write_text(vbs_content)
os.system(f'cscript //nologo "{vbs_path}"')
vbs_path.unlink()

print(f"Desktop shortcut created: {shortcut_path}")
