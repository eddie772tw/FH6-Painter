# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('tools\\bin\\*', 'tools\\bin'), ('tools\\fh6-heuristics.json', 'tools'), ('settings\\*', 'settings'), ('lang\\*', 'lang')]
binaries = []
hiddenimports = ['utils', 'evaluators.numba_kernels', 'evaluators.numba_evaluator', 'evaluators.taichi_evaluator', 'evaluators.go_opencl_evaluator', 'tools.fh6_import_layer_table', 'tools.fh6_painter_generator']
tmp_ret = collect_all('taichi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('numba')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('llvmlite')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['D:\\FH6-Painter\\backend\\server.py'],
    pathex=['D:\\FH6-Painter\\.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='server-sidecar-x86_64-pc-windows-msvc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
