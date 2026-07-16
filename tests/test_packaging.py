import os
import re


def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_ignored_dirs():
    root_dir = get_project_root()
    ignore_file = os.path.join(root_dir, ".pkgdirignore")
    assert os.path.exists(ignore_file), f"找不到打包排除設定檔: {ignore_file}"

    ignored_dirs = set()
    with open(ignore_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 忽略註解與空白行
            if line and not line.startswith("#"):
                ignored_dirs.add(line)
    return ignored_dirs


def test_packaging_includes_all_resource_directories():
    """確保所有根目錄下且未被忽略的資源資料夾（例如 'lang'、'settings'、'tools' 等）
    都已被正確設定在 `build_release.bat` 及 PyInstaller `*.spec` 設定中進行打包。
    """
    root_dir = get_project_root()
    ignored_dirs = load_ignored_dirs()

    # 1. 找出專案中所有應被打包的資源資料夾
    actual_resource_dirs = []
    for name in os.listdir(root_dir):
        path = os.path.join(root_dir, name)
        if os.path.isdir(path) and name not in ignored_dirs:
            actual_resource_dirs.append(name)

    # 確保我們有找到資源資料夾（目前至少應有 lang, settings, tools）
    assert len(actual_resource_dirs) > 0, "沒有在根目錄下找到任何需要被打包的資源資料夾"

    # 2. 讀取打包設定檔
    bat_path = os.path.join(root_dir, "build_release.bat")
    spec_path = os.path.join(root_dir, "FH6-Painter.spec")

    assert os.path.exists(bat_path), f"找不到打包腳本: {bat_path}"
    assert os.path.exists(spec_path), f"找不到 spec 檔案: {spec_path}"

    with open(bat_path, "r", encoding="utf-8") as f:
        bat_content = f.read()

    with open(spec_path, "r", encoding="utf-8") as f:
        spec_content = f.read()

    # 3. 逐一驗證資源資料夾是否有被設定打包
    for rdir in actual_resource_dirs:
        # (已移除舊版的 build_release.bat --add-data 檢查，現在統一使用 spec 檔案配置)

        # 檢查 spec 檔案的 datas 變數是否包含該目錄設定
        # 格式：('rdir\\*', 'rdir') 或 ('rdir/*', 'rdir') 等
        has_in_spec = False
        spec_pattern = (
            rf'[\'"]{re.escape(rdir)}[\s\\/*\'"]*,\s*[\'"]{re.escape(rdir)}[\'"]'
        )
        if (
            re.search(spec_pattern, spec_content)
            or f"'{rdir}\\" in spec_content
            or f'"{rdir}\\' in spec_content
            or f"'{rdir}/" in spec_content
            or f'"{rdir}/' in spec_content
        ):
            has_in_spec = True

        assert has_in_spec, (
            f"根目錄下發現新的資源資料夾 '{rdir}'，但似乎未在 `FH6-Painter.spec` 的 datas 中進行配置。\n"
            f"若該資料夾需要打包發行，請將其新增至 spec 檔案的 `datas` 中。\n"
            f"若不需要打包，請將其列入 `tests/test_packaging.py` 的 `IGNORED_ROOT_DIRS` 中。"
        )
