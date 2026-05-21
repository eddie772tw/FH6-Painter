# FH6-Painter 🎨
> **Forza Horizon 6 JIT-Accelerated Image-to-Livery Painter & Memory Importer**  
> **基於 Numba JIT 加速的極速《極限競速：地平線 6》圖片轉車貼與記憶體匯入工具**

[![Language](https://img.shields.io/badge/Language-Python%203.12%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Acceleration](https://img.shields.io/badge/JIT%20Acceleration-Numba-orange.svg)](https://numba.pydata.org/)

---

## 🌟 核心特色 / Key Features

### 🇹🇼 中文說明
1. **極致的 JIT 編譯效能**：全 Python 重構核心，利用 Numba 進行動態 JIT 編譯與多核心並行隨機搜尋（Parallel Random Search），生成速度比純 Python 快達數十倍，完全免除編譯 C++ 執行檔的繁瑣需求。
2. **多功能平底化 GUI 介面**：提供專業的 Tkinter 圖形操作面板 (`fh6_painter_studio_gui.py`)，支援拖曳輸入、即時生成預覽、動態設定調整與一鍵智能匯入。
3. **安全免管理員權限 (Bypass UAC)**：利用特殊環境變數繞過 Windows UAC 強制系統管理員權限的需求，保證執行安全且避免彈出權限提示。
4. **JIT 記憶體雙向優化**：
   - **中途冗餘消除**：生成過程中每 100 層自動進行一次「反向遮蔽遮罩 (Backward Alpha Occlusion)」運算，移除完全被蓋住的無用形狀。
   - **末尾形狀保留**：最終將無用形狀重置為左上角 `(0,0)` 且 `100% 透明` 的極小圖形，既符合 Forza 遊戲車貼層數限制，又能保持畫面的絕對純淨。
5. **智能記憶體掃描匯入**：利用 Windows API (`ReadProcessMemory`/`WriteProcessMemory`) 於背景安全定位 `LiveryGroup` 記憶體表，數秒內即可將複雜的數千層車貼無縫寫入《極限競速：地平線 6》中。

### 🇬🇧 English Description
1. **High-Performance JIT Compilation**: Core rewritten entirely in Python and JIT-compiled/parallel-optimized using Numba. Up to tens of times faster than standard python interpreters, bypassing any need for complex C++ toolchains.
2. **Feature-Rich Tkinter GUI**: A beautiful, flat-design graphical studio (`fh6_painter_studio_gui.py`) featuring drag-and-drop input, real-time visual progress previews, interactive parameter settings, and one-click smart importing.
3. **UAC Bypass & Secure Running**: Bypasses mandatory Windows administrator privileges via environment wrappers, preventing annoying prompt interruptions and keeping the execution secure.
4. **Dual JIT-Powered Optimizations**:
   - **Midway Redundancy Check**: Automatically scans shapes every 100 layers during generation using backward-tracing alpha occlusion filters to eliminate fully covered shapes.
   - **Final Shape Reservation**: Resets occluded redundant shapes into microscopic, `100% transparent` ellipses located at `(0,0)`, preserving exact layer limits in game while guaranteeing canvas cleanliness.
5. **Direct Memory Injector**: Safely scans game process RAM and writes vector data directly into the active `LiveryGroup` layers table within seconds using native win32 memory APIs.

---

## 📂 專案架構 / Folder Layout

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
├── test_img/                  # 測試圖片目錄 (Git已忽略) / Test images folder (Git-ignored)
├── output/                    # 幾何JSON輸出目錄 (Git已忽略) / Vector JSON output (Git-ignored)
└── tools/
    ├── fh_import_layer_table.py # 記憶體掃描與寫入核心 / Win32 RAM scanner & injector
    └── fh_painter_generator.py  # Numba JIT 圖片轉形狀核心 / JIT shape generator core
```

---

## 🛠️ 安裝與依賴需求 / Prerequisites & Installation

本專案需要 **Python 3.12 或更高版本**。

1. **複製本儲存庫 / Clone the Repository**:
   ```bash
   git clone https://github.com/eddie772tw/FH6-Painter.git
   cd FH6-Painter
   ```

2. **安裝 Python 依賴 / Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 使用指南 / How to Use

### 第一步：產生車貼幾何資料 / Step 1: Generate Vector JSON

#### 🟢 方法 A：使用專業版 GUI 介面（推薦 / Recommended）
1. 雙擊執行 `forza-painter-py.bat` 或在終端機運行：
   ```bash
   python fh6_painter_studio_gui.py
   ```
2. 將要轉換的圖片拖曳至介面中的 **「選擇目標圖片」** 框。
3. 選擇您想要的設定檔（例如預設的 `c. balanced`）。
4. 點選 **「開始生成 (Start Generation)」**。您可以在右側看見高畫質的即時畫布生成預覽！
5. 生成完成後，幾何 JSON 將自動保存在 `output/` 目錄中。

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

## ⚖️ 開源授權與致謝 / License & Credits

本專案採用 **MIT 授權條款** 開源。  
本專案為完全的 Python 重構版，核心幾何算法與匯入技術部分衍生並致謝自以下優秀的開源項目：

* **MIT License**：Copyright (c) 2026 罐頭 (eddie772tw) & 貢獻者。
* **Original C++ forza-painter** by [AE (A-Dawg#0001)](https://github.com/forza-painter/forza-painter) — 提供原版 C++ 邏輯參考。
* **geometrize-lib** by [Sam Twidale](https://samcodes.co.uk/) — 啟發形狀生成理論。
* **Primitive library** by [Michael Fogleman](https://github.com/fogleman/primitive) — 啟發最初的幾何擬合算法。
