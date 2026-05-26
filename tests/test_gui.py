#!/usr/bin/env python3
import os
import sys
import tkinter as tk
import pytest
from fh6_painter_studio_gui import ForzaStudioGUI, HAS_LIBS

# 使用 PEP8 / Google Style / Black Style 規範

def test_gui_initialization():
    """測試 Tkinter GUI 控制面板的初始化與安全載入。"""
    # 如果是在 Linux Headless 且沒有 Xvfb 模擬顯示器的極端環境下跑本地測試，跳過測試
    if sys.platform != "win32" and not os.environ.get("DISPLAY"):
        pytest.skip("無 X 顯示伺服器，跳過 GUI 載入測試（在 CI/CD 中將使用 xvfb 執行）")

    # 初始化 Tkinter root
    root = tk.Tk()
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

    finally:
        # 安全銷毀視窗，避免執行緒阻塞或記憶體殘留
        root.destroy()
