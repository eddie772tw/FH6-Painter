import os
import sys
import tkinter as tk

# --- Real-time Log Redirector for GUI Diagnostics ---
global_log_buffer = []


class LogRedirector:
    def __init__(self, buffer_list, original_stream=None):
        self.buffer_list = buffer_list
        self.original_stream = original_stream

    def write(self, string):
        self.buffer_list.append(string)
        if self.original_stream is not None:
            try:
                self.original_stream.write(string)
            except Exception:
                pass

    def flush(self):
        if self.original_stream is not None:
            try:
                self.original_stream.flush()
            except Exception:
                pass


def setup_logging():
    sys.stdout = LogRedirector(global_log_buffer, sys.stdout)
    sys.stderr = LogRedirector(global_log_buffer, sys.stderr)


def get_project_root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- ToolTip classes ---
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hide_tip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.show_tip)

    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)

    def show_tip(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("tahoma", "8", "normal"),
        )
        label.pack(ipadx=1)

    def hide_tip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


def create_tooltip(widget, text):
    if not hasattr(widget, "_tooltip"):
        widget._tooltip = ToolTip(widget, text)
    else:
        widget._tooltip.text = text


def remove_tooltip(widget):
    if hasattr(widget, "_tooltip"):
        widget._tooltip.hide_tip()
        widget.unbind("<Enter>")
        widget.unbind("<Leave>")
        del widget._tooltip


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hide_tip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.show_tip)

    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)

    def show_tip(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#2e2e2e",
            foreground="#e0e0e0",
            relief="solid",
            border=1,
            font=("Microsoft JhengHei", 9),
            padx=8,
            pady=6,
        )
        label.pack(ipadx=1)

    def hide_tip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


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
