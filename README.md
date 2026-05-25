# FH6-Painter 🎨
> **Forza Horizon 6 Heterogeneous JIT-Accelerated Image-to-Livery Painter & Memory Importer**  
> **基於JIT加速的極速《極限競速：地平線 6》車貼生成與記憶體匯入工具**

[![Language](https://img.shields.io/badge/Language-Python%203.12%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Acceleration](https://img.shields.io/badge/JIT%20Acceleration-Numba%20%26%20Taichi-orange.svg)](https://numba.pydata.org/)

---

## 簡介 / Introduction & Summary
基本上就是一個用Python重新寫的forza-painter，但更快、更好而且支援Forza Horizon 6。
支援透過Numba(CPU)或Taichi(GPU)加速，以及提供了GUI和更連貫的導入體驗。
Basically a rebuild of forza-painter using Python, but much faster and support Forza Horizon 6.
Support both CPU and GPU JIT acceleration, provide GUI & smooth import expierence.

## 專案架構 / Folder Layout

```text
├── fh6_painter_launcher.py    # 控制台拖曳啟動器 / Drag-and-drop CLI launcher
├── fh6_painter_studio_gui.py  # 專業版圖形控制面板 / Professional Tkinter Studio GUI
├── forza-painter-py.bat       # 啟動腳本 / Easy startup batch script
├── LICENSE                    # MIT 開源授權條款 / Open-source License
├── requirements.txt           # 依賴套件表 / Python dependencies list
├── settings/                  # 各種生成速率與品質預設設定 / Generation presets
│   ├── a. keemstar fast...ini
│   ├── c. balanced...         # 預設平衡設定檔 / Default balanced configuration
│   └── g. i hate my pc...ini  
├── evaluators/                # JIT 評估器核心組件目錄 / JIT Evaluator plugins
│   ├── __init__.py            # 評估器載入工廠 / Evaluator Factory
│   ├── taichi_evaluator.py    # GPU Vulkan 評估器 / GPU Taichi JIT Evaluator
│   ├── numba_evaluator.py     # CPU 多線程評估器 / CPU Numba JIT Evaluator
│   └── pure_python_evaluator.py # CPU 基準評估器 / Pure Python Evaluator Baseline
├── test_img/                  # 測試圖片目錄 (Git已忽略) / Test images folder
├── output/                    # 幾何JSON輸出目錄 (Git已忽略) / Vector JSON output
└── tools/
    ├── fh_import_layer_table.py # 記憶體掃描與寫入核心 / Win32 RAM scanner & injector
    ├── fh6_painter_generator.py # JIT 幾何生成器 / JIT shape generator tool
    └── benchmark_taichi.py      # 跨解析度效能對決分析腳本 / Cross-res JIT Profiler
```

---

## 安裝與依賴需求 / Prerequisites & Installation

本專案需要 **Python 3.12 或更高版本**。

1. **複製本儲存庫 / Clone the Repository**:
   ```bash
   git clone https://github.com/eddie772tw/FH6-Painter.git
   cd FH6-Painter
   ```

2. **安裝依賴**:
   ```bash
   pip install -r requirements.txt
   ```
	或直接啟動 `forza-painter-py.bat`也可以實現自動部署。
---

## 使用指南 / How to Use

### 第一步：產生車貼幾何資料 / Step 1: Generate Vector JSON

#### 🟢 方法 A：使用專業版 GUI 介面（推薦 / Recommended）
1. 雙擊執行 `forza-painter-py.bat` 或在終端機運行：
   ```bash
   python fh6_painter_studio_gui.py
   ```
2. 將要轉換的圖片拖曳至介面中的 **「選擇目標圖片」** 框。
3. 選擇使用的 JIT 引擎。
4. 點選 **「開始生成 (Start Generation)」**。您可以在右側看見高畫質的即時畫布生成預覽！同時診斷主控台會實時輸出運算資訊。

#### 🔵 方法 B：拖曳至啟動器（CLI 快速模式 / CLI Fast Mode）
* 將您的圖片拖曳至 `fh6_painter_launcher.py` 或 `forza-painter-py.bat` 圖示上，隨後依提示選擇層數限制與設定檔，即會於背景自動執行生成。

---

### 第二步：匯入至《極限競速：地平線 6》 / Step 2: Import into Forza Horizon 6

1. 啟動 **《極限競速：地平線 6》 (Forza Horizon 6)** 遊戲。
2. 進入 **車庫 ➔ 設計與塗裝 ➔ 建立車貼群組 (Vinyl Group Editor)**。
3. **載入一個全新、完全未群組化（Ungrouped）的圓球 (Sphere) 範本**，層數需大於或等於您剛才生成的幾何層數（例如 2000 層或 3000 層）。
4. 保持遊戲於該畫面，並回到 **FH6-Painter GUI**。
5. 點選 **「一鍵匯入記憶體 (Memory Import)」**，或直接將生成的 JSON 拖曳至 `fh6_painter_launcher.py` 上。
6. Importer 會自動安全地掃描遊戲記憶體定位圖層表。首次掃描約需一至二分鐘（後續同視窗下執行會讀取快取秒速完成），完成定位後即會以極速自動將幾何向量寫入遊戲中！

---

##  開源授權與致謝 / License & Credits

* **MIT License**：Copyright (c) 2026 罐頭 (eddie772tw) & 貢獻者。
* **Original C++ forza-painter** by [AE (A-Dawg#0001)](https://github.com/forza-painter/forza-painter) — 提供原版 C++ 邏輯參考。
* **geometrize-lib** by [Sam Twidale](https://samcodes.co.uk/) — 啟發形狀生成理論。
* **Primitive library** by [Michael Fogleman](https://github.com/fogleman/primitive) — 啟發最初的幾何擬合算法。
