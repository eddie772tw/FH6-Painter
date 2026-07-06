#!/usr/bin/env python3
"""環境指紋收集 — CPU / GPU / RAM / Git 資訊。"""
import platform

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def get_cpu_model():
    """Reads precise CPU brand name on Windows/Linux/macOS."""
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            return cpu_name.strip()
        except Exception:
            pass
    return platform.processor() or "Unknown CPU"


def get_gpu_list():
    """Reads GPU model description using native winreg on Windows."""
    gpus = []
    if platform.system() == "Windows":
        try:
            import winreg
            path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        if subkey_name.isdigit():
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                gpu_name, _ = winreg.QueryValueEx(subkey, "DriverDesc")
                                if gpu_name and gpu_name not in gpus:
                                    gpus.append(gpu_name)
                    except Exception:
                        pass
        except Exception:
            pass
    return gpus if gpus else ["Unknown GPU Device"]


def get_gpu_driver_version():
    """抓取精準的 GPU 驅動版本。"""
    if platform.system() == "Windows":
        try:
            import subprocess
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader,nounits"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
            if out:
                return f"NVIDIA {out}"
        except Exception:
            pass

        try:
            import winreg
            path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        if subkey_name.isdigit():
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                drv_version, _ = winreg.QueryValueEx(subkey, "DriverVersion")
                                if drv_version:
                                    return drv_version
                    except Exception:
                        pass
        except Exception:
            pass
    return "N/A"


def get_ram_size():
    if HAS_PSUTIL:
        return f"{psutil.virtual_memory().total / (1024**3):.1f} GB"
    return "Unknown RAM"


def get_git_info():
    """Gathers current Git branch, commit hash, and last message summary."""
    try:
        import subprocess
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        msg = subprocess.check_output(["git", "log", "-1", "--pretty=%s"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        return {"commit": commit, "branch": branch, "message": msg}
    except Exception:
        return {"commit": "N/A", "branch": "N/A", "message": "N/A"}
