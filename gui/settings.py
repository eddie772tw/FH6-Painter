import json
import os
import re

from gui.utils import get_project_root


class SettingsMixin:
    def validate_geometry(self, geom_str, screen_w, screen_h):
        """解析並校驗視窗幾何字串，防止視窗小於 1216x863 或移出可見螢幕範圍之外"""
        pattern = r"^(\d+)x(\d+)([+-]\d+)?([+-]\d+)?$"
        match = re.match(pattern, geom_str.strip())

        default_w = 1216
        default_h = 863

        if not match:
            # 解析失敗，使用預設值置中
            x = max(0, (screen_w - default_w) // 2)
            y = max(0, (screen_h - default_h) // 2)
            return f"{default_w}x{default_h}+{x}+{y}"

        w = int(match.group(1))
        h = int(match.group(2))
        x_str = match.group(3)
        y_str = match.group(4)

        # 確保大小始終不小於 1216x863
        if w < default_w:
            w = default_w
        if h < default_h:
            h = default_h

        if x_str is None or y_str is None:
            # 沒有位置資訊，則居中
            x = max(0, (screen_w - w) // 2)
            y = max(0, (screen_h - h) // 2)
            return f"{w}x{h}+{x}+{y}"

        x = int(x_str)
        y = int(y_str)

        # 螢幕邊界安全檢查防護：
        # 1. 標題列頂部不可移出螢幕上方 (y < 0)
        # 2. 視窗頂部不能低於螢幕底部的 100 像素以內 (y > screen_h - 100)
        # 3. 視窗右邊不能小於左邊 100 像素 (x + w < 100)
        # 4. 視窗左邊不能大於螢幕右邊的 100 像素以內 (x > screen_w - 100)
        # 如果不符合安全條件，則強制將其置中。
        if y < 0 or y > screen_h - 100 or x + w < 100 or x > screen_w - 100:
            x = max(0, (screen_w - w) // 2)
            y = max(0, (screen_h - h) // 2)

        x_part = f"+{x}" if x >= 0 else str(x)
        y_part = f"+{y}" if y >= 0 else str(y)
        return f"{w}x{h}{x_part}{y_part}"

    def load_optimization_settings(self):
        """載入或初始化優化設定 JSON 檔"""
        if not getattr(self, "settings_path", None):
            self.settings_path = os.path.join(
                get_project_root(), "optimization_settings.json"
            )
        default_settings = {
            "window_geometry": "1216x863",
            "image_pyramid": {"enabled": False, "fine_phase_layer": 500},
            "importance_sampling": {"enabled": False, "update_interval": 10},
            "simulated_annealing": {
                "enabled": False,
                "initial_temp": 10.0,
                "cooling_rate": 0.95,
            },
            "dynamic_freeze": {
                "enabled": False,
                "update_interval": 100,
                "error_threshold": 3,
            },
            "error_weighting": {"enabled": False, "update_interval": 100},
            "decaying_shape": {"enabled": False, "min_max_r": 5.0},
            "uncovered_bias": {"enabled": True, "bias": 5.0},
            "boundary_weighting": {"enabled": True, "bias": 3.0},
        }

        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    self.opt_settings = json.load(f)
                # 確保所有必要鍵都存在
                for k, v in default_settings.items():
                    if k not in self.opt_settings:
                        self.opt_settings[k] = v
                    elif isinstance(v, dict):
                        for sub_k, sub_v in v.items():
                            if sub_k not in self.opt_settings[k]:
                                self.opt_settings[k][sub_k] = sub_v
            except Exception as e:
                self.log_to_console(
                    f"[Settings] 讀取優化設定失敗: {e}，正在重建設定檔並恢復預設值。\n"
                )
                self.opt_settings = default_settings
                self.save_optimization_settings()
        else:
            self.opt_settings = default_settings
            self.save_optimization_settings()

        # 套用儲存的視窗幾何尺寸與位置
        geom = self.opt_settings.get("window_geometry", "1216x863")
        try:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            validated_geom = self.validate_geometry(geom, screen_w, screen_h)
            self.root.geometry(validated_geom)
        except Exception as e:
            self.log_to_console(
                f"[Settings] 套用視窗幾何失敗: {e}，回退到 1216x863 置中。\n"
            )
            try:
                screen_w = self.root.winfo_screenwidth()
                screen_h = self.root.winfo_screenheight()
                x = max(0, (screen_w - 1216) // 2)
                y = max(0, (screen_h - 863) // 2)
                self.root.geometry(f"1216x863+{x}+{y}")
            except Exception:
                self.root.geometry("1216x863")

    def save_optimization_settings(self):
        """保存優化設定到 JSON 檔"""
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.opt_settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log_to_console(f"[Settings] 儲存優化設定失敗: {e}\n")

    def on_opt_changed(self):
        """當優化設定 Checkbox 被點擊時，更新並保存設定"""
        self.opt_settings["image_pyramid"]["enabled"] = self.var_pyramid.get()
        self.opt_settings["importance_sampling"]["enabled"] = self.var_importance.get()
        self.opt_settings["simulated_annealing"]["enabled"] = self.var_annealing.get()
        self.opt_settings["dynamic_freeze"]["enabled"] = self.var_freeze.get()
        self.opt_settings["error_weighting"]["enabled"] = self.var_weight.get()
        self.opt_settings["decaying_shape"]["enabled"] = self.var_decay.get()
        self.save_optimization_settings()
        self.log_to_console("[Settings] 已更新優化設定至 JSON 檔\n")
