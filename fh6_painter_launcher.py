#!/usr/bin/env python3
import glob
import json
import os
import subprocess
import sys


def is_json(path):
    return path.lower().endswith(".json")


def count_importable_shapes(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            root = json.load(f)
        raw_shapes = root.get("shapes", [])
        count = 0
        for raw in raw_shapes:
            if is_forza_painter_canvas_header(raw):
                continue
            count += 1
        return count
    except Exception as e:
        print(f"Warning: Could not count shapes in JSON: {e}")
        return 2000


def is_forza_painter_canvas_header(raw):
    # type=1, data=[0,0,width,height], alpha=0
    shape_type = raw.get("type", 0)
    data = raw.get("data", [])
    color = raw.get("color", [])
    if shape_type != 1:
        return False
    return (
        len(data) >= 4
        and abs(float(data[0])) < 0.0001
        and abs(float(data[1])) < 0.0001
        and len(color) >= 4
        and int(color[3]) == 0
    )


def pick_template_layer_count(json_path):
    importable_shapes = count_importable_shapes(json_path)
    if importable_shapes <= 1500:
        return 1500
    if importable_shapes <= 2000:
        return 2000
    return 3000


def ask_layer_count(path):
    detected = pick_template_layer_count(path) if is_json(path) else 2000
    print()
    print(f"File: {os.path.basename(path)}")
    if is_json(path):
        print(f"Detected JSON recommendation: {detected} layers")
    print("FH6 limits: front/rear bumper 1000, left/right/top up to 3000.")
    sys.stdout.write(f"How many layers? [default {detected}, allowed 5-3000]: ")
    sys.stdout.flush()
    try:
        user_input = sys.stdin.readline().strip()
    except KeyboardInterrupt:
        sys.exit(1)

    if not user_input:
        return detected
    try:
        val = int(user_input)
        val = max(5, min(3000, val))
        return val
    except ValueError:
        return detected


def build_save_at(layer_count):
    values = []
    for n in range(500, layer_count, 500):
        values.append(n)
    if layer_count not in values:
        values.append(layer_count)
    return ",".join(str(v) for v in values)


def replace_setting(text, key, value):
    lines = text.replace("\r\n", "\n").split("\n")
    replaced = False
    for i in range(len(lines)):
        if lines[i].lower().startswith(key.lower() + " ="):
            lines[i] = f"{key} = {value}"
            replaced = True

    if not replaced:
        if lines and lines[-1] == "":
            lines[-1] = f"{key} = {value}"
        else:
            lines.append(f"{key} = {value}")

    return "\r\n".join(lines)


def update_profiles_for_layer_count(root, layer_count):
    settings_dir = os.path.join(root, "settings")
    if not os.path.isdir(settings_dir):
        return

    save_at = build_save_at(layer_count)
    ini_files = glob.glob(os.path.join(settings_dir, "*.ini"))
    for file in ini_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                text = f.read()
            text = replace_setting(text, "saveAt", save_at)
            text = replace_setting(text, "stopAt", str(layer_count))
            with open(file, "w", encoding="utf-8", newline="") as f:
                f.write(text)
        except Exception as e:
            print(f"Warning: Failed to update profile {os.path.basename(file)}: {e}")

    print(f"Updated generator profiles: stopAt={layer_count}, saveAt={save_at}")


def check_python_dependencies():
    """Checks if the required libraries are installed."""
    try:
        import numpy as np
        from PIL import Image

        return True
    except ImportError:
        return False


def list_profiles(root):
    """Lists all available settings profiles with their parsed descriptions."""
    settings_dir = os.path.join(root, "settings")
    if not os.path.isdir(settings_dir):
        return []

    ini_files = glob.glob(os.path.join(settings_dir, "*.ini"))
    ini_files.sort()

    profiles = []
    for filepath in ini_files:
        filename = os.path.basename(filepath)
        if filename.startswith("_"):  # Ignore default template in selection
            continue
        description = "No description / 無描述"
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.lower().startswith(
                        "description ="
                    ) or line.lower().startswith("description="):
                        description = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
        profiles.append(
            {
                "path": filepath,
                "name": filename[:-4],  # Strip .ini extension
                "description": description,
            }
        )
    return profiles


def ask_profile(root):
    """Prompts the user to select an INI profile from settings/."""
    profiles = list_profiles(root)
    if not profiles:
        print(
            "Warning: No profiles found in settings/ directory. / 警告：未在 settings/ 中找到任何配置檔。"
        )
        return None

    print("\n--- 可用的產生器配置檔 / Available Generator Profiles ---")
    for idx, p in enumerate(profiles):
        print(f"[{idx + 1}] {p['name']} - {p['description']}")

    # Auto-select balanced profile as default if possible
    default_idx = 0
    for idx, p in enumerate(profiles):
        if "balanced" in p["name"].lower() or "c." in p["name"].lower():
            default_idx = idx
            break

    sys.stdout.write(
        f"請選擇配置檔 / Choose profile [預設/default {default_idx + 1} - {profiles[default_idx]['name']}]: "
    )
    sys.stdout.flush()
    try:
        user_input = sys.stdin.readline().strip()
    except KeyboardInterrupt:
        sys.exit(1)

    if not user_input:
        return profiles[default_idx]["path"]
    try:
        val = int(user_input) - 1
        if 0 <= val < len(profiles):
            return profiles[val]["path"]
    except ValueError:
        pass
    return profiles[default_idx]["path"]


def run_cmd(exe, arguments, cwd=None):
    print(f"{os.path.basename(exe)} {' '.join(arguments)}")
    try:
        # Enforce the __COMPAT_LAYER=RunAsInvoker environment variable to bypass UAC elevation requirements
        env = os.environ.copy()
        env["__COMPAT_LAYER"] = "RunAsInvoker"
        res = subprocess.run(
            [exe] + arguments, cwd=cwd or os.path.dirname(exe) or None, env=env
        )
        return res.returncode
    except Exception as e:
        print(f"Error running command: {e}")
        return 1


def main():
    try:
        root = os.path.dirname(os.path.abspath(__file__))
        original_painter = os.path.join(root, "forza-painter.exe")
        importer = os.path.join(root, "tools", "fh6_import_layer_table.py")
        py_generator = os.path.join(root, "tools", "fh6_painter_generator.py")

        args = sys.argv[1:]
        if not args:
            print(
                "請拖曳圖片檔案（產生 JSON）或 JSON 檔案（匯入 FH6 記憶體）至此腳本上運行。",
                file=sys.stderr,
            )
            print(
                "Drop PNG/JPG files here to generate JSON, or drop JSON files here to import into FH6.",
                file=sys.stderr,
            )
            try:
                input("Press Enter to close...")
            except EOFError:
                pass
            return 2

        exit_code = 0
        for path in args:
            layer_count = ask_layer_count(path)
            if is_json(path):
                if not os.path.exists(importer):
                    raise FileNotFoundError(f"FH6 importer not found: {importer}")
                print(f"Using FH6 target template: {layer_count} layers")
                # Run importer using current Python executable
                exit_code = run_cmd(
                    sys.executable,
                    [importer, path, f"--layers={layer_count}"],
                    cwd=root,
                )
            else:
                has_py_deps = check_python_dependencies()
                use_py_generator = False

                # Check generator options
                if not os.path.exists(original_painter):
                    print(
                        "\n[INFO] 未偵測到 C++ forza-painter.exe，自動啟用高效能 Python 幾何圖形產生器。"
                    )
                    use_py_generator = True
                elif has_py_deps:
                    print("\n偵測到同時支援 C++ 執行檔與 Python 加速產生器。")
                    print(
                        "[1] Pure Python Generator (Numba JIT 加速，免系統管理員權限) [推薦]"
                    )
                    print("[2] C++ forza-painter.exe (原版可執行檔)")
                    sys.stdout.write(
                        "請選擇產生器類型 / Select generator [預設/default 1]: "
                    )
                    sys.stdout.flush()
                    try:
                        choice = sys.stdin.readline().strip()
                    except KeyboardInterrupt:
                        sys.exit(1)
                    if choice == "2":
                        use_py_generator = False
                    else:
                        use_py_generator = True
                else:
                    use_py_generator = False

                if use_py_generator:
                    if not os.path.exists(py_generator):
                        raise FileNotFoundError(
                            f"Python generator script not found at: {py_generator}"
                        )
                    if not has_py_deps:
                        raise ImportError(
                            "Python shape generator requires 'pillow' and 'numpy'. Please run: pip install pillow numpy"
                        )

                    profile_path = ask_profile(root)

                    args_list = [py_generator, path, f"--layers={layer_count}"]
                    if profile_path:
                        args_list.append(f"--profile={profile_path}")

                    print("\n[INFO] 正在啟動 Python 高效能 JIT 形狀產生器...")
                    exit_code = run_cmd(sys.executable, args_list, cwd=root)
                else:
                    # Run original C++ painter with bypass UAC compat layer
                    update_profiles_for_layer_count(root, layer_count)
                    exit_code = run_cmd(original_painter, [path], cwd=root)

            if exit_code != 0:
                try:
                    input("Press Enter to close...")
                except EOFError:
                    pass
                return exit_code

        return exit_code
    except Exception as ex:
        print(f"ERROR: {ex}", file=sys.stderr)
        try:
            input("Press Enter to close...")
        except EOFError:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
