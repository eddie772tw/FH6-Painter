# FH6-Painter 🎨
> **Forza Horizon 6 Triple Heterogeneous Accelerated Image-to-Livery Painter & Memory Importer**
> **基於三重異質加速的極速《極限競速：地平線 6》車貼生成與記憶體匯入工具**

[![Language](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Acceleration](https://img.shields.io/badge/Acceleration-Go--OpenCL%20%26%20Taichi%20%26%20Numba-orange.svg)](https://numba.pydata.org/)
[![Package](https://img.shields.io/badge/Distribution-Standalone%20EXE-red.svg)](dist/FH6-Painter)

---

## 簡介 / Introduction & Summary
基本上就是一個用Python重新寫的forza-painter，但更快、更好而且支援Forza Horizon 6。
支援透過Go-OpenCL(GPU)、Taichi(GPU)或Numba(CPU)三種異質運算加速，以及提供了GUI和更連貫的導入體驗。
Basically a rebuild of forza-painter using Python, but much faster and support Forza Horizon 6.
Support Go-OpenCL, Taichi, and Numba acceleration across CPU and GPU, provide GUI & smooth import experience.

---

## 核心特性 / Core Features

*   **三重異質加速支援**：整合 Go-OpenCL (GPU)、Taichi (GPU) 與 Numba (CPU)，為不同硬體提供極致效能的幾何擬合計算。
*   **專業暗黑科技風格 Studio GUI**：提供實時幾何擬合工作台預覽，以及包含層數、生成速度與剩餘時間 (ETA) 等實時數據 HUD 看板。
*   **實時畫布區域重繪 (ROI Painting)**：允許用戶在畫布上直接框選特定區域 (矩形/橢圓) 進行重新擬合，自動略過不需修改的背景，實現局部精細修復與優化。
*   **歷史回溯與重續 (History Rewind)**：允許隨時退回指定層數並從該點重新生成。
*   **文字車貼生成器 (Text Vinyl Generator)**：內建工具可直接將文字轉換為形狀層的 JSON 車貼格式。
*   **效能基準測試面板 (Performance Benchmark Console)**：內建跑分工具可評估 CPU 與 GPU 的幾何擬合運算效能。
*   **一鍵診斷主控台 (Show Logs)**：GUI 內建實時主控台，即便在無視窗發行版下也能 100% 捕獲背景日誌與 Traceback 錯誤資訊。
*   **高效 Win32 記憶體掃描匯入引擎**：透過快取與啟發式匹配，數秒內安全將幾何向量寫入遊戲中。
*   **綠色免安裝獨立執行檔 (.exe)**：支援一鍵編譯為單機 EXE，且主配置與預設資料夾完全維持在外置同層目錄，便於攜帶與自訂。

*   **Triple Heterogeneous Acceleration**: Integrate Go-OpenCL (GPU), Taichi (GPU), and Numba (CPU) to provide top-tier geometry fitting performance across different hardware configurations.
*   **Premium Dark Tech Style Studio GUI**: Provide real-time canvas preview of geometry fitting and live HUD metrics for current layers, generation speed, and estimated remaining time (ETA).
*   **Region of Interest (ROI) Painting**: Allows users to select specific areas on the canvas for targeted refitting, automatically ignoring the rest of the image to achieve fine-grained local refinement.
*   **History Rewind**: Allows rewinding back to a specific layer count and resuming generation from that point at any time.
*   **Text Vinyl Generator**: Built-in tool to directly convert text into shape layers JSON format.
*   **Performance Benchmark Console**: Built-in benchmark suite to evaluate CPU and GPU geometry fitting performance.
*   **One-Click Diagnostic Console**: Integrated real-time console that captures 100% of background stdout/stderr logs and tracebacks even in windowed standalone mode.
*   **High-Performance Win32 Memory Injector**: Safely scan FH6's layer table memory and hot-inject JSON liveries within seconds using heuristics caching.
*   **Portable Standalone Executable (.exe)**: Support compiling into a single portable EXE with external configuration directories for easy customization and portability.

---

## 專案架構 / Folder Layout

```text
├── build_release.bat          # 一鍵編譯獨立 Windows 執行檔腳本 / One-click EXE Bundler
├── forza-painter-py.bat       # 啟動與自動依賴部署腳本 / Auto-venv Setup & Startup batch
├── backend/                   # Python WebSocket 後端 / Python WebSocket Backend
├── frontend/                  # Tauri 現代化圖形前端 / Tauri Modern GUI Frontend
├── optimization_settings.json # 全局效能與排程配置 / Global Performance & Scheduling Settings
├── fh6_painter_launcher.py    # 控制台拖曳啟動器 / Drag-and-drop CLI launcher
├── requirements.txt           # 專案 Python 依賴清單 / Python dependencies list
├── pyproject.toml             # Ruff 程式碼規範與格式化配置 / Ruff code style configs
├── .pkgdirignore              # 打包排除目錄配置 / Directory exclusion settings for bundling
├── settings/                  # 各種生成速率與品質預設配置 / Generation presets
│   ├── a. keemstar fast...ini
│   ├── c. balanced...         # 預設平衡配置檔 / Default balanced configuration
│   └── g. i hate my pc...ini  
├── evaluators/                # JIT 評估器核心組件目錄 / JIT Evaluator plugins
│   ├── __init__.py            # 評估器載入工廠 / Evaluator Factory (含 3.14 防護機制)
│   ├── base_evaluator.py      # 基礎評估器類別 / Base Evaluator Class
│   ├── go_opencl_evaluator.py # Go-OpenCL 最速評估器 / Go-OpenCL GPU Evaluator
│   ├── taichi_evaluator.py    # GPU Vulkan/CUDA 評估器 / GPU Taichi JIT Evaluator
│   ├── numba_evaluator.py     # CPU 多線程評估器 / CPU Numba JIT Evaluator
│   └── numba_kernels.py       # Numba 核心計算邏輯 / Numba Kernels
├── tools/                     # 核心工具箱 / Project core toolbox
│   ├── benchmark/             # 效能跑分套件 / Benchmark Suite Package
│   ├── bin/                   # 外部二進位工具目錄 / External Binaries
│   ├── fh6-heuristics.json    # 記憶體掃描快取 / Memory scan heuristics
│   ├── fh6_import_layer_table.py # 記憶體掃描與寫入核心 / Win32 RAM scanner & injector
│   ├── fh6_painter_generator.py  # JIT 幾何生成器 / JIT shape generator tool
│   ├── test_pso_optimizer.py  # PSO 最佳化測試 / PSO optimizer test
│   ├── text_generator.py      # 文字生成器 / Text generator tool
│   └── verify_boundary.py     # 邊界驗證工具 / Boundary validation tool
├── lang/                      # 多國語系與本地化設定檔 / Locales and translation files (Built-in: English, Japanese, Traditional Chinese)
├── tests/                     # 測試套件 / Test suites
```

---

## 安裝與執行說明 / Prerequisites & Execution

*   **方法 A：獨立免安裝版本（推薦 / Recommended）**：
    1. 前往 Release 頁面下載最新獨立發行版 `FH6-Painter` ZIP 包。
    2. 解壓縮後直接雙擊執行 **`FH6-Painter.exe`** 即可。您可以直接修改同目錄下的 `settings/` 預設配置與 `optimization_settings.json`。
*   **方法 B：開發原始碼版（需要 Python 環境與 Node.js）**：
    專案原生支援 **Python 3.13**（支援全部 CPU/GPU 引擎），並相容 **Python 3.14**（僅支援 Go-OpenCL 與 Numba 加速，Taichi 將自動停用）。需安裝 **Node.js** 以編譯與執行前端環境。選裝 **Rust (cargo)** 可用於原生 Tauri 應用編譯。
    1. 複製儲存庫：`git clone https://github.com/eddie772tw/FH6-Painter.git`
    2. 直接雙擊啟動 **`forza-painter-py.bat`**。該腳本會全自動偵測、建立 Python 3.13 虛擬環境 (`.venv`) 並安裝所有依賴，同時也會透過 npm 安裝前端套件，隨後啟動程式。也可以手動安裝依賴：`pip install -r requirements.txt`、`pip install -r backend/requirements.txt` 與 `npm --prefix frontend install`。

*   **Method A: Standalone Portable Version (Recommended)**:
    1. Download the latest standalone release `FH6-Painter` ZIP package from the Release page.
    2. Unzip and double-click **`FH6-Painter.exe`** to run. You can directly edit the `settings/` presets and `optimization_settings.json` located beside the executable.
*   **Method B: Source Code Version (Requires Python & Node.js)**:
    Native support for **Python 3.13** (Full CPU/GPU engines) and compatible with **Python 3.14** (Go-OpenCL and Numba JIT only; Taichi automatically disabled). **Node.js** is required to compile and run the frontend environment. **Rust (cargo)** is optional but recommended for native Tauri app compilation.
    1. Clone the repository: `git clone https://github.com/eddie772tw/FH6-Painter.git`
    2. Double-click **`forza-painter-py.bat`** to start. The script will automatically detect Python, create a Python 3.13 virtual environment (`.venv`), install Python requirements, install npm dependencies, and run the app. You can also install requirements manually: `pip install -r requirements.txt`, `pip install -r backend/requirements.txt` and `npm --prefix frontend install`.

---

## 使用指南 / How to Use

### 第一步：產生車貼幾何資料 / Step 1: Generate Livery Geometry JSON

*   **🟢 方法 A：使用專業版 GUI 介面（推薦 / Recommended）**：
    1. 雙擊執行發行版中 **`FH6-Painter.exe`** 或開發版中的 **`forza-painter-py.bat`**。
    2. 將要轉換的圖片拖曳至左側 **「1. INPUT SOURCE」** 的輸入框中。
    3. 點選 **「開始生成 (Start Generation)」**。您可以在右側看見即時畫布生成預覽與實時指標 HUD！
*   **🔵 方法 B：拖曳至啟動器（CLI 快速模式 / CLI Fast Mode）**：
    1. 將您的圖片拖曳至 `fh6_painter_launcher.py` 圖示上。
    2. 依提示選擇層數限制與設定檔，即會於背景自動執行生成。

*   **🟢 Method A: Using Premium Studio GUI (Recommended)**:
    1. Double-click **`FH6-Painter.exe`** in the release bundle or **`forza-painter-py.bat`** in the source folder.
    2. Drag and drop the target image into the **"1. INPUT SOURCE"** input field on the left.
    3. Click **"Start Generation"** to view real-time canvas fitting and live HUD metrics.
*   **🔵 Method B: Drag to Launcher (CLI Fast Mode)**:
    1. Drag your image directly onto the `fh6_painter_launcher.py` icon.
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
*   **排除非發行資源目錄 / Exclude Non-release Directories (.pkgdirignore)**：
    *   專案根目錄下的 **`.pkgdirignore`** 檔案用於定義不需要打包進 `.exe` 中的目錄（例如：環境變數 `.venv`、開發暫存目錄 `build`、測試程式 `tests` 等）。
    *   當執行 `build_release.bat` 時，腳本會自動掃描根目錄。若發現有新增的資料夾既不在 `.pkgdirignore` 中、也未在打包指令中進行 `--add-data` 配置，將會主動彈出互動提示：
        *   **輸入 Y**：自動將該資料夾新增至 `.pkgdirignore` 以在未來忽略它。
        *   **輸入 N**（超時 10 秒亦為 N）：警示開發者需要手動將其加入打包設定，並中止建置流程。
    *   The **`.pkgdirignore`** file in the root directory manages folders excluded from the standalone bundle. If a folder is unregistered (not listed in `.pkgdirignore` and not included in `--add-data` options), `build_release.bat` will prompt you:
        *   **Press Y**: Automatically append the folder to `.pkgdirignore`.
        *   **Press N** (default after 10s timeout): Cancel the build and warn you to manually configure the packaging settings.

---

## 新增自訂語系支援 / Adding New Translations

本專案支援完全動態加載的多語言框架，貢獻者無需修改任何程式碼即可新增新語系：
The project supports a fully dynamic multi-language framework. Contributors can add new languages without changing any code:

1. **建立語系檔 / Create Localized JSON**:
   在 `lang/` 目錄下建立一個符合 ISO 639 與 locale 定義的 JSON 檔案（例如 `fr-fr.json`）。可以直接複製 `lang/en-us.json` 作為範本進行翻譯。
   Create a JSON file named after the ISO 639 locale code (e.g. `fr-fr.json`) inside the `lang/` directory. You can copy `lang/en-us.json` as a starting template.

2. **註冊語言名稱 / Register Locale Name**:
   編輯 `lang/iso639.json`，在字典中加入該語系代碼與對應的人性化易讀名稱。例如：
   Edit `lang/iso639.json` and append your locale code mapping to its readable language name. For example:
   ```json
   {
     "fr-fr": "Français (French)"
   }
   ```
   *註：若未在此註冊，下拉選單中將直接顯示其原始檔名（Fallback）。*
   *Note: If not registered, the select dropdown will display the raw filename code as a fallback.*

3. **語系 PR 提交規範 / Pull Request Guidelines for Translations**:
   當提交新的語系支援 PR 時，請遵循以下標準化格式：
   When submitting a Pull Request for new language support, please follow these standardized formatting rules:
   
   - **PR 標題格式 / PR Title**: `feat(i18n): add <locale-name> language support` (例如 `feat(i18n): add French (fr-fr) language support`)。
   - **PR 說明內容 / PR Description Template**:
     ```markdown
     ## 語系新增說明 / Translation Details
     - 新增語系代碼 / Added Locale Code: `fr-fr`
     - 語系顯示名稱 / Display Language Name: `Français (French)`

     ## 檢查清單 / Checklist
     - [ ] 已在 `lang/` 目錄建立對應的 `<locale-code>.json` 檔案
     - [ ] 已在 `lang/iso639.json` 中註冊此語系代碼與對照名稱
     - [ ] 翻譯 JSON 中的所有翻譯鍵（Keys）皆已完整對齊 `en-us.json`
     - [ ] 確認翻譯內容中無殘留的中文字元或錯位
     - [ ] 已在本地測試過，選單能正常加載並正確切換該語系
     - [ ] 已在本地手動執行並通過 i18n 單元測試 (Run and passed: `pytest tests/test_i18n.py`)
     ```

---

## 開發者規範與程式碼格式化 / Developer Guide & Formatting

專案採用 **[Ruff](https://github.com/astral-sh/ruff)** 作為標準的程式碼格式化與風格檢查工具。為確保代碼風格一致，並能順利通過 GitHub Actions 的 CI 檢查，請在提交代碼前遵循以下程序進行格式化：

*   **全量格式化代碼 / Reformat All Code**：
    ```bash
    # 在虛擬環境外 / Outside venv
    ruff format .

    # 在 Windows 虛擬環境內 / Inside Windows venv
    .venv\Scripts\ruff.exe format .
    ```
*   **驗證排版格式 / Verify Code Formatting**：
    ```bash
    # 在虛擬環境外 / Outside venv
    ruff format --check .

    # 在 Windows 虛擬環境內 / Inside Windows venv
    .venv\Scripts\ruff.exe format --check .
    ```

---

## 開源授權與致謝 / License & Credits

*   **MIT License**：Copyright (c) 2026 罐頭 (eddie772tw) & 貢獻者。
*   **Original C++ forza-painter** by [AE (A-Dawg#0001)](https://github.com/forza-painter/forza-painter) — 提供原版 C++ 邏輯與記憶體圖表結構參考。
*   **geometrize-lib** by [Sam Twidale](https://samcodes.co.uk/) — Numba與Taichi JIT引擎使用的幾何擬合演算法。
*   **Primitive library** by [Michael Fogleman](https://github.com/fogleman/primitive) — 實踐上述演算法的程式碼基礎。
*   **GO-OpenCL Engine Support** by [神龟](https://github.com/zjl88858/forza-painter-geometrize-gpu) - 引入該開發者提出的另一種更高效的GPU實現。
*   **forza-painter-fh6** by [bvzrays](https://github.com/bvzrays/forza-painter-fh6) — 提供進階記憶體讀寫實作、JSON 格式標準化與 painter6.com 市場整合機制之重要參考與技術啟發。
