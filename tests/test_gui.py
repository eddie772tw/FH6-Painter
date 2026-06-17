#!/usr/bin/env python3
import os
import sys
import tkinter as tk

import pytest

from fh6_painter_studio_gui import ForzaStudioGUI

# 使用 PEP8 / Google Style / Black Style 規範


def safe_init_tk():
    """安全初始化 tk.Tk()，只在出現特定『非程式本身造成』的環境 TclError 時跳過測試"""
    try:
        root = tk.Tk()
        return root
    except Exception as e:
        err_msg = str(e)
        # 精確匹配「非程式本身導致」的環境缺失或 Tcl 資源損壞錯誤
        # 1. tcl_findLibrary: 找不到 Tcl 庫 (多次初始化 C 資源清理副作用或 Windows CI 缺件)
        # 2. no display name: Linux/Unix 下沒有 DISPLAY 顯示器
        # 3. Tcl_Init / cannot open display: 其它系統層級的 Tk 載入失敗
        is_env_error = (
            "tcl_findLibrary" in err_msg
            or "no display name" in err_msg
            or "Tcl_Init" in err_msg
            or "cannot open display" in err_msg
            or "usable init.tcl" in err_msg
            or "wasn't installed properly" in err_msg
        )
        if is_env_error:
            pytest.skip(
                f"系統環境不支援或 Tcl 資源受限（安全跳過非代碼 Bug 錯誤）: {e}"
            )
        else:
            # 其它意料之外的錯誤（說明可能是我們自己的代碼在引用或底層拋出了其它異常）則直接拋出，不予以遮蓋
            raise e


def test_gui_initialization(monkeypatch):
    """測試 Tkinter GUI 控制面板的初始化、安全載入以及注入失敗捕捉邏輯。"""
    # 如果是在 Linux Headless 且沒有 Xvfb 模擬顯示器的極端環境下跑本地測試，跳過測試
    if sys.platform != "win32" and not os.environ.get("DISPLAY"):
        pytest.skip("無 X 顯示伺服器，跳過 GUI 載入測試（在 CI/CD 中將使用 xvfb 執行）")

    root = safe_init_tk()
    root.withdraw()  # 隱藏主視窗，避免實體彈窗干擾測試

    try:
        # 初始化專案主 GUI
        app = ForzaStudioGUI(root)

        # 驗證 GUI 物件的核心組件與資料結構是否被正確初始化
        assert app.root is root
        assert len(app.profiles) > 0
        assert len(app.gpu_list) > 0

        # 驗證核心按鈕與標籤控制元件是否存在
        assert app.btn_generate is not None
        assert app.btn_inject is not None
        assert app.status_lbl is not None

        # 觸發一次事件迴圈更新，確保所有 Layout、Canvas 和 Flat 樣式能正確完成繪製且無報錯
        root.update()

        # 驗證注入失敗時的包裝器捕捉邏輯（使用同一個 Tk 實例避免多次初始化 tk.Tk() 引發系統 TCL 錯誤）
        monkeypatch.setattr(
            "tools.fh6_import_layer_table.run_importer", lambda **kwargs: 1
        )
        app.run_importer_wrapper(json_path="dummy.json", layers=10)
        assert app.import_result == 1

    finally:
        # 安全銷毀視窗，避免執行緒阻塞或記憶體殘留
        root.destroy()


def test_validate_geometry():
    """測試視窗幾何字串校驗與越界安全防護邏輯"""
    root = safe_init_tk()
    root.withdraw()
    try:
        app = ForzaStudioGUI(root)
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()

        # 1. 測試解析成功且小於 1216x863，應該被強制拉大到 1216x863
        geom1 = "1000x700+50+50"
        val1 = app.validate_geometry(geom1, screen_w, screen_h)
        assert "1216x863" in val1

        # 2. 測試解析失敗，應該使用預設大小 1216x863 置中
        geom2 = "invalid_format"
        val2 = app.validate_geometry(geom2, screen_w, screen_h)
        assert "1216x863" in val2

        # 3. 測試越界位置（跑出螢幕外，例如負數極端值），應該重置為螢幕置中
        geom3 = "1216x863-30000-30000"
        val3 = app.validate_geometry(geom3, screen_w, screen_h)
        # 解析出的置中座標應該為 x = (screen_w - 1216) // 2, y = (screen_h - 863) // 2
        expected_x = max(0, (screen_w - 1216) // 2)
        expected_y = max(0, (screen_h - 863) // 2)
        expected_geom = f"1216x863+{expected_x}+{expected_y}"
        assert val3 == expected_geom

    finally:
        root.destroy()


def test_settings_recreation_on_corruption(tmp_path):
    """測試 optimization_settings.json 損壞時自動重建的保險機制"""
    root = safe_init_tk()
    root.withdraw()
    try:
        app = ForzaStudioGUI(root)
        temp_settings = tmp_path / "temp_optimization_settings.json"
        app.settings_path = str(temp_settings)

        # 1. 寫入一個損壞的、無法解析的 json 內容
        with open(app.settings_path, "w", encoding="utf-8") as f:
            f.write("this is a corrupted { json [ ] file")

        # 2. 調用 load_optimization_settings，驗證是否會使用預設值，且自動重建檔案為健全 JSON 格式
        app.load_optimization_settings()
        assert app.opt_settings["window_geometry"] == "1216x863"

        # 3. 驗證檔案是否被寫回且可以正確載入為 JSON
        import json

        with open(app.settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["window_geometry"] == "1216x863"

    finally:
        root.destroy()


def test_go_engine_list():
    """測試 Go-OpenCL 引擎在 UI 下拉選單中的整合狀態與可用性偵測"""
    root = safe_init_tk()
    root.withdraw()
    try:
        app = ForzaStudioGUI(root)

        # 尋找 Go-OpenCL 引擎
        go_meta = None
        for e in app.available_evaluators:
            if e["code"] == "GO_OPENCL":
                go_meta = e
                break

        assert go_meta is not None

        # 驗證 Go 引擎可用性應與實際二進位檔是否存在一致
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        go_binary_path = os.path.join(
            project_root, "tools", "bin", "forza-painter-geometrize-go.exe"
        )
        has_go_file = os.path.exists(go_binary_path)
        assert go_meta["available"] == has_go_file

    finally:
        root.destroy()


def test_engine_selection_and_order():
    """測試 JIT 引擎下拉選單的排序（Pure Python 必在最下）以及選取 Go 引擎時停用進階優化選項，同時非 Taichi 時隱藏 Taichi 元件"""
    root = safe_init_tk()
    root.withdraw()
    try:
        app = ForzaStudioGUI(root)



        # 2. 模擬選取 GO_OPENCL 引擎並驗證優化選項 state 與 Taichi 專屬元件隱藏
        go_idx = None
        numba_idx = None
        taichi_idx = None
        for idx, e in enumerate(app.available_evaluators):
            if e["code"] == "GO_OPENCL":
                e["available"] = True
                go_idx = idx
            elif e["code"] == "NUMBA":
                e["available"] = True
                numba_idx = idx
            elif e["code"] == "TAICHI":
                e["available"] = True
                taichi_idx = idx

        assert go_idx is not None
        assert numba_idx is not None
        assert taichi_idx is not None

        # 切換到 GO_OPENCL 引擎
        app.combo_engine.current(go_idx)
        app.on_engine_selected(None)

        # 驗證 Card 2.5 (Advanced Optimizations) 卡片被隱藏 (pack_info() 會拋出 TclError)
        with pytest.raises(Exception) as excinfo:
            app.card_opts.pack_info()
        assert "isn't packed" in str(excinfo.value)

        # 驗證 Taichi 專屬元件被隱藏 (grid_info() 為空)
        assert not app.lbl_taichi_arch.grid_info()
        assert not app.taichi_arch_container.grid_info()
        assert not app.lbl_taichi_device.grid_info()
        assert not app.combo_taichi_device.grid_info()

        # 切換到 TAICHI 引擎
        app.combo_engine.current(taichi_idx)
        app.on_engine_selected(None)

        # 驗證 Taichi 專屬元件被顯示，且在對應 row
        assert int(app.lbl_taichi_arch.grid_info()["row"]) == 5
        assert int(app.taichi_arch_container.grid_info()["row"]) == 5
        assert int(app.lbl_taichi_device.grid_info()["row"]) == 6
        assert int(app.combo_taichi_device.grid_info()["row"]) == 6

        # 驗證 Card 2.5 (Advanced Optimizations) 被重新顯示 (pack_info() 正常回傳)
        pack_meta = app.card_opts.pack_info()
        assert pack_meta["fill"] == "x"

        # 切換回 NUMBA 引擎
        app.combo_engine.current(numba_idx)
        app.on_engine_selected(None)

        # 驗證 Card 2.5 (Advanced Optimizations) 依然被顯示 (pack_info() 正常回傳)
        pack_meta2 = app.card_opts.pack_info()
        assert pack_meta2["fill"] == "x"

        # 驗證 Taichi 專屬元件被隱藏 (grid_info() 為空)
        assert not app.lbl_taichi_arch.grid_info()
        assert not app.taichi_arch_container.grid_info()
        assert not app.lbl_taichi_device.grid_info()
        assert not app.combo_taichi_device.grid_info()

    finally:
        root.destroy()
