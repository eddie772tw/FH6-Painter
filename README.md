# FH6-Painter 🎨
> **Forza Horizon 6 Heterogeneous JIT-Accelerated Image-to-Livery Painter & Memory Importer**
> **基於異質 JIT 加速的極速《極限競速：地平線 6》車貼生成與記憶體匯入工具**

[![Language](https://img.shields.io/badge/Language-Python%203.13%20%2F%203.14%20(CPU)--blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Acceleration](https://img.shields.io/badge/JIT%20Acceleration-Numba%20%26%20Taichi-orange.svg)](https://numba.pydata.org/)
[![Package](https://img.shields.io/badge/Distribution-Standalone%20EXE-red.svg)](dist/FH6_Painter_Studio)

---

## 簡介 / Introduction & Summary
基本上就是一個用Python重新寫的forza-painter，但更快、更好而且支援Forza Horizon 6。
支援透過Numba(CPU)或Taichi(GPU)加速，以及提供了GUI和更連貫的導入體驗。
Basically a rebuild of forza-painter using Python, but much faster and support Forza Horizon 6.
Support both CPU and GPU JIT acceleration, provide GUI & smooth import expierence.

---

## 核心特性 / Core Features

*   **雙重異質 JIT 加速**：利用 Numba (CPU) 與 Taichi (GPU) 在執行期將幾何擬合演算法編譯為高效核心碼，極速計算。
*   **專業暗黑科技風格 Studio GUI**：提供實時幾何擬合工作台預覽，以及包含層數、生成速度與剩餘時間 (ETA) 等實時數據 HUD 看板。
*   **一鍵診斷主控台 (Show Logs)**：GUI 內建實時主控台，即便在無視窗發行版下也能 100% 捕獲背景日誌與 Traceback 錯誤資訊。
*   **高效 Win32 記憶體掃描匯入引擎**：透過快取與啟發式匹配，數秒內安全將幾何向量寫入遊戲中。
*   **綠色免安裝獨立執行檔 (.exe)**：支援一鍵編譯為單機 EXE，且主配置與預設資料夾完全維持在外置同層目錄，便於攜帶與自訂。

*   **Heterogeneous Dual-Engine JIT Acceleration**: Leverage Numba (CPU) and Taichi (GPU) to compile geometry fitting algorithms into high-performance machine code at runtime, significantly boosting efficiency.
*   **Premium Dark Tech Style Studio GUI**: Provide real-time canvas preview of geometry fitting and live HUD metrics for current layers, generation speed, and estimated remaining time (ETA).
*   **One-Click Diagnostic Console**: Integrated real-time console that captures 100% of background stdout/stderr logs and tracebacks even in windowed standalone mode.
*   **High-Performance Win32 Memory Injector**: Safely scan FH6's layer table memory and hot-inject JSON liveries within seconds using heuristics caching.
*   **Portable Standalone Executable (.exe)**: Support compiling into a single portable EXE with external configuration directories for easy customization and portability.

---

## 專案架構 / Folder Layout

```text
├── build_release.bat          # 一鍵編譯獨立 Windows 執行檔腳本 / One-click EXE Bundler
├── forza-painter-py.bat       # 啟動與自動依賴部署腳本 / Auto-venv Setup & Startup batch
├── fh6_painter_studio_gui.py  # 專業版圖形控制面板 / Professional Tkinter Studio GUI
├── fh6_painter_launcher.py    # 控制台拖曳啟動器 / Drag-and-drop CLI launcher
├── requirements.txt           # 專案 Python 依賴清單 / Python dependencies list
├── settings/                  # 各種生成速率與品質預設配置 / Generation presets
│   ├── a. keemstar fast...ini
│   ├── c. balanced...         # 預設平衡配置檔 / Default balanced configuration
│   └── g. i hate my pc...ini
├── evaluators/                # JIT 評估器核心組件目錄 / JIT Evaluator plugins
│   ├── __init__.py            # 評估器載入工廠 / Evaluator Factory (含 3.14 防護機制)
│   ├── taichi_evaluator.py    # GPU Vulkan/CUDA 評估器 / GPU Taichi JIT Evaluator
│   ├── numba_evaluator.py     # CPU 多線程評估器 / CPU Numba JIT Evaluator
│   └── pure_python_evaluator.py # CPU 基準評估器 / Pure Python Evaluator Baseline
├── tools/                     # 核心工具箱 / Project core toolbox
│   ├── fh6_import_layer_table.py # 記憶體掃描與寫入核心 / Win32 RAM scanner & injector
│   ├── fh6_painter_generator.py # JIT 幾何生成器 / JIT shape generator tool
│   └── benchmark_taichi.py      # 效能對決分析腳本 / Cross-res JIT Profiler
```

---

## 安裝與執行說明 / Prerequisites & Execution

*   **方法 A：獨立免安裝版本（推薦 / Recommended）**：
    1. 前往 Release 頁面下載最新獨立發行版 `FH6_Painter_Studio` ZIP 包。
    2. 解壓縮後直接雙擊執行 **`FH6_Painter_Studio.exe`** 即可。您可以直接修改同目錄下的 `settings/` 預設配置與 `optimization_settings.json`。
*   **方法 B：開發原始碼版（需要 Python 環境）**：
    專案原生支援 **Python 3.13**（支援 CPU/GPU 雙 JIT 加速），並相容 **Python 3.14**（僅支援 Numba CPU 加速，Taichi GPU 模式將自動停用）。
    1. 複製儲存庫：`git clone https://github.com/eddie772tw/FH6-Painter.git`
    2. 直接雙擊啟動 **`forza-painter-py.bat`**。該腳本會全自動偵測、建立 Python 3.13 虛擬環境 (`.venv`) 並安裝所有依賴，隨後啟動程式。也可以手動安裝依賴：`pip install -r requirements.txt`。

*   **Method A: Standalone Portable Version (Recommended)**:
    1. Download the latest standalone release `FH6_Painter_Studio` ZIP package from the Release page.
    2. Unzip and double-click **`FH6_Painter_Studio.exe`** to run. You can directly edit the `settings/` presets and `optimization_settings.json` located beside the executable.
*   **Method B: Source Code Version (Requires Python)**:
    Native support for **Python 3.13** (Full dual CPU/GPU JIT acceleration) and compatible with **Python 3.14** (CPU Numba JIT only; Taichi GPU mode automatically disabled).
    1. Clone the repository: `git clone https://github.com/eddie772tw/FH6-Painter.git`
    2. Double-click **`forza-painter-py.bat`** to start. The script will automatically detect Python, create a Python 3.13 virtual environment (`.venv`), install requirements, and run the app. You can also install requirements manually: `pip install -r requirements.txt`.

---

## 使用指南 / How to Use

### 第一步：產生車貼幾何資料 / Step 1: Generate Livery Geometry JSON

*   **🟢 方法 A：使用專業版 GUI 介面（推薦 / Recommended）**：
    1. 雙擊執行發行版中 **`FH6_Painter_Studio.exe`** 或開發版中的 **`forza-painter-py.bat`**。
    2. 將要轉換的圖片拖曳至左側 **「1. INPUT SOURCE」** 的輸入框中。
    3. 點選 **「開始生成 (Start Generation)」**。您可以在右側看見即時畫布生成預覽與實時指標 HUD！
*   **🔵 方法 B：拖曳至啟動器（CLI 快速模式 / CLI Fast Mode）**：
    1. 將您的圖片拖曳至 `fh6_painter_launcher.py` 或 `forza-painter-py.bat` 圖示上。
    2. 依提示選擇層數限制與設定檔，即會於背景自動執行生成。

*   **🟢 Method A: Using Premium Studio GUI (Recommended)**:
    1. Double-click **`FH6_Painter_Studio.exe`** in the release bundle or **`forza-painter-py.bat`** in the source folder.
    2. Drag and drop the target image into the **"1. INPUT SOURCE"** input field on the left.
    3. Click **"Start Generation"** to view real-time canvas fitting and live HUD metrics.
*   **🔵 Method B: Drag to Launcher (CLI Fast Mode)**:
    1. Drag your image directly onto `fh6_painter_launcher.py` or the `forza-painter-py.bat` icon.
    2. Follow the prompt to choose layers limit and presets, then let the generator run in the background.

> [!TIP]
> 如果您遇到 GPU 錯誤或想查看背景進度，請點選 GUI 右上角的 **「診斷主控台 / Show Logs」** 按鈕，即可在極客綠字終端機中實時看到包含 Taichi 初始化、VRAM 分配以及冗餘檢查在內的所有背景日誌與 traceback 資訊。
> If you encounter GPU errors or want to monitor background progress, click the **"診斷主控台 / Show Logs"** button in the top-right header to view Taichi initialization, VRAM allocations, and detailed tracebacks in the live terminal console.

### 第二步：匯入至《極限競速：地平線 6》 / Step 2: Import into Forza Horizon 6

*   **匯入步驟**：
    1. 啟動 **《極限競速：地平線 6》** 遊戲，進入 **車庫 ➔ 設計與塗裝 ➔ 建立車貼群組**。
    2. **載入一個全新、完全未群組化且層數足夠的圓球範本**（如 2000 層）。
    3. 保持遊戲於該畫面，點選 GUI 上的 **「一鍵匯入記憶體 (Memory Import)」**，數秒內即可將車貼自動寫入遊戲！
*   **Import Steps**:
    1. Start **Forza Horizon 6**, go to **Garage ➔ Designs & Paints ➔ Create Vinyl Group**.
    2. **Load a brand new, completely ungrouped sphere template** with sufficient layers (e.g. 2000 layers).
    3. Keep the game on that screen, click **"Memory Import"** on the GUI, and the livery will be hot-injected into the game within seconds!

---

## 自行打包與發行 / Build Standalone Release (.exe)

*   **二進位打包**：
    *   若您修改了原始碼並想自己編譯一份發行版，可直接雙擊專案根目錄下的 **`build_release.bat`**。
    *   它將全自動清理暫存檔、全量收集 Taichi 原始碼、打包 DLL 並配發外置資源，生成一個免安裝的 Release ZIP 包。
*   **Compiling Standalone Release**:
    *   If you modified the source code and want to compile your own standalone release, double-click **`build_release.bat`** in the project root.
    *   It will clean temporary files, gather Taichi source code, package DLLs, and copy external presets to compile a standalone Release ZIP.

---

## 開源授權與致謝 / License & Credits

*   **MIT License**：Copyright (c) 2026 罐頭 (eddie772tw) & 貢獻者。
*   **Original C++ forza-painter** by [AE (A-Dawg#0001)](https://github.com/forza-painter/forza-painter) — 提供原版 C++ 邏輯與記憶體圖表結構參考。
*   **geometrize-lib** by [Sam Twidale](https://samcodes.co.uk/) — 幾何擬合算法理論啟發。
*   **Primitive library** by [Michael Fogleman](https://github.com/fogleman/primitive) — 啟發最初的幾何擬合核心。
