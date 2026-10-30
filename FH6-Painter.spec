# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# 1. 自動收集大型、複雜庫（Taichi, Numba, LLVmlite）的所有二進位檔與資料
datas = []
binaries = []
hiddenimports = [
    "utils",
    "evaluators.numba_kernels",
    "evaluators.numba_evaluator",
    "evaluators.taichi_evaluator",
    "evaluators.go_opencl_evaluator",
    "tools.fh6_import_layer_table",
    "tools.fh6_painter_generator"
]

# 收集 taichi
t_datas, t_bins, t_hidden = collect_all("taichi")
datas += t_datas
binaries += t_bins
hiddenimports += t_hidden

# 收集 numpy (fix for ModuleNotFoundError: No module named 'numpy._core._exceptions' in numpy 2.x)
np_datas, np_bins, np_hidden = collect_all("numpy")
datas.extend(np_datas)
binaries.extend(np_bins)
hiddenimports.extend(np_hidden)

# Explicity include module since `collect_all` does not properly pull in numpy._core._exceptions
hiddenimports.extend([
    "numpy",
    "numpy._core",
    "numpy._core._exceptions",
    "numpy._core._machar"
])

# 收集 numba
tmp_datas, tmp_binaries, tmp_hiddenimports = collect_all('numba')
datas.extend(tmp_datas)
binaries.extend(tmp_binaries)
hiddenimports.extend(tmp_hiddenimports)

# 收集 llvmlite
tmp_datas, tmp_binaries, tmp_hiddenimports = collect_all('llvmlite')
datas.extend(tmp_datas)
binaries.extend(tmp_binaries)
hiddenimports.extend(tmp_hiddenimports)


# 2. 手動定義靜態資源與 Tauri 前端編譯產出的 exe
# 格式為: (來源路徑, 打包到 exe 內部的相對目標目錄)
added_files = [
    # 專案靜態資料夾
    ('tools/bin/*', 'tools/bin'),
    ('tools/fh6-heuristics.json', 'tools'),
    ('settings/*', 'settings'),
    ('lang/*', 'lang'),
    ('evaluators/*.py', 'evaluators'),
    
    # 關鍵：將 Tauri 編譯產出的 frontend.exe 封裝進去（目標放在根目錄）
    ('frontend/src-tauri/target/release/frontend.exe', '.'),
]

datas.extend(added_files)


# 3. 分析與打包核心設定
a = Analysis(
    [os.path.join('backend', 'server.py')], # 入口程式碼
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PIL._imagingcms',
        'PIL.ImageCms',
        'PIL._webp',
        'PIL._imagingtk',
        'PIL.ImageTk',
        'PIL._imagingmorph'
    ], # 排除不需要的 Pillow 子模組以減輕體積
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FH6-Painter',       # 產出的 EXE 檔名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                 # 避免病毒誤報
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # False 等同於 --windowed (不顯示控制台視窗)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
	icon="app_icon.ico",
	version=os.path.join(os.path.abspath('.'), 'file_version_info.txt'),
)