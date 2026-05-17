"""
create_shortcut.py – Create a desktop shortcut for Keyboard Forest.
Tries .lnk via PowerShell first, falls back to a .bat launcher.
"""

import os
import sys
import subprocess


def create_desktop_shortcut() -> bool:
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    python_exe = sys.executable
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
    work_dir = os.path.dirname(script_path)

    # Try .lnk via PowerShell
    lnk_path = os.path.join(desktop, "键盘森林.lnk")
    if not os.path.exists(lnk_path):
        try:
            ps_script = (
                f'$ws = New-Object -ComObject WScript.Shell; '
                f'$sc = $ws.CreateShortcut("{lnk_path}"); '
                f'$sc.TargetPath = "{python_exe}"; '
                f'$sc.Arguments = \\"{script_path}\\"; '
                f'$sc.WorkingDirectory = "{work_dir}"; '
                f'$sc.WindowStyle = 1; '
                f'$sc.Description = "键盘森林"; '
                f'$sc.Save()'
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True, timeout=10
            )
            if result.returncode == 0 and os.path.exists(lnk_path):
                return True
        except Exception:
            pass

    # Fallback 1: .vbs launcher (no console window)
    vbs_path = os.path.join(desktop, "键盘森林.vbs")
    if not os.path.exists(vbs_path):
        try:
            vbs_content = (
                f'Set ws = CreateObject("WScript.Shell")\n'
                f'ws.Run Chr(34) & "{python_exe}" & Chr(34) & " " & '
                f'Chr(34) & "{script_path}" & Chr(34), 0, False\n'
            )
            with open(vbs_path, "w", encoding="utf-8") as f:
                f.write(vbs_content)
            if os.path.exists(vbs_path):
                return True
        except Exception:
            pass

    # Fallback 2: .bat file shortcut
    bat_path = os.path.join(desktop, "键盘森林.bat")
    if not os.path.exists(bat_path):
        try:
            bat_content = (
                f'@echo off\n'
                f'cd /d "{work_dir}"\n'
                f'start "" "{python_exe}" "{script_path}"\n'
            )
            with open(bat_path, "w", encoding="gbk") as f:
                f.write(bat_content)
            return True
        except Exception:
            pass

    return os.path.exists(lnk_path) or os.path.exists(vbs_path) or os.path.exists(bat_path)


if __name__ == "__main__":
    success = create_desktop_shortcut()
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if success:
        print("桌面快捷方式已创建！")
        lnk = os.path.join(desktop, "键盘森林.lnk")
        vbs = os.path.join(desktop, "键盘森林.vbs")
        bat = os.path.join(desktop, "键盘森林.bat")
        for f in [lnk, vbs, bat]:
            if os.path.exists(f):
                print(f"  {f}")
    else:
        print("创建失败。请手动将以下内容保存为桌面快捷方式：")
        print(f"  目标: {sys.executable}")
        print(f"  参数: {os.path.abspath('main.py')}")
