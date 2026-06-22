import os
import sys


def get_project_root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scan_profiles():
    """Scans the 'settings' directory for available .ini configurations."""
    profiles = []
    settings_dir = os.path.join(get_project_root(), "settings")
    if os.path.exists(settings_dir):
        for f in os.listdir(settings_dir):
            if f.endswith(".ini"):
                path = os.path.join(settings_dir, f)
                desc = "No description available."
                # Parse description
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        for line in file:
                            if line.strip().startswith("description"):
                                parts = line.split("=", 1)
                                if len(parts) == 2:
                                    desc = parts[1].strip()
                                break
                except Exception:
                    pass
                profiles.append(
                    {
                        "filename": f,
                        "name": os.path.splitext(f)[0],
                        "path": path,
                        "desc": desc,
                    }
                )
    # If empty, add a default profile stub
    if not profiles:
        profiles.append(
            {
                "filename": "_default.ini",
                "name": "_default",
                "path": "",
                "desc": "Default system generation profile",
            }
        )
    # Sort alphabetically first
    profiles.sort(key=lambda x: x["name"])
    # Move "c. balanced" profile to the front (index 0) so it's selected by default
    balanced_idx = -1
    for idx, p in enumerate(profiles):
        if "balanced" in p["name"].lower():
            balanced_idx = idx
            break
    if balanced_idx != -1:
        balanced_item = profiles.pop(balanced_idx)
        profiles.insert(0, balanced_item)
    elif len(profiles) > 0:
        default_idx = -1
        for idx, p in enumerate(profiles):
            if p["name"] == "_default":
                default_idx = idx
                break
        if default_idx != -1:
            default_item = profiles.pop(default_idx)
            profiles.insert(0, default_item)
    return profiles


def scan_gpus():
    """偵測系統中的顯示卡列表 (支援 winreg 登錄檔、wmic 與 PowerShell 多重防禦機制)"""
    gpus = []

    # 定義排除關鍵字 (不區分大小寫)
    exclude_keywords = [
        "display adapter",
        "parsec",
        "remote",
        "virtual",
        "indirect",
        "mirror",
    ]

    def is_valid_gpu(name):
        if not name:
            return False
        name_lower = name.lower()
        return not any(kw in name_lower for kw in exclude_keywords)

    # 1. 優先採用 Python 原生 winreg 讀取登錄檔 (速度最快，免行程開銷，完全不受 wmic 棄用影響)
    try:
        import winreg

        path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    if subkey_name.isdigit():
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            try:
                                gpu_name, _ = winreg.QueryValueEx(subkey, "DriverDesc")
                                if (
                                    gpu_name
                                    and gpu_name not in gpus
                                    and is_valid_gpu(gpu_name)
                                ):
                                    gpus.append(gpu_name)
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception:
        pass

    # 2. 次要備援方案：wmic 指令 (以 stderr=DEVNULL 靜音)
    if not gpus:
        try:
            import subprocess

            out = subprocess.check_output(
                "wmic path win32_VideoController get name",
                shell=True,
                stderr=subprocess.DEVNULL,
            ).decode("utf-8", errors="ignore")
            lines = [line.strip() for line in out.split("\n") if line.strip()]
            if len(lines) > 1:
                for l in lines[1:]:
                    if (
                        l
                        and "name" not in l.lower()
                        and l not in gpus
                        and is_valid_gpu(l)
                    ):
                        gpus.append(l)
        except Exception:
            pass

    # 3. 終極備援方案：PowerShell 原生 CimInstance 查詢
    if not gpus:
        try:
            import subprocess

            out = subprocess.check_output(
                'powershell -Command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"',
                shell=True,
                stderr=subprocess.DEVNULL,
            ).decode("utf-8", errors="ignore")
            lines = [line.strip() for line in out.split("\n") if line.strip()]
            for l in lines:
                if l and l not in gpus and is_valid_gpu(l):
                    gpus.append(l)
        except Exception:
            pass

    if not gpus:
        gpus = ["Default GPU (Device 0)"]
    return gpus
