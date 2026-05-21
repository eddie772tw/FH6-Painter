#!/usr/bin/env python3
import sys
import os
import subprocess
import glob
import json

def is_json(path):
    return path.lower().endswith('.json')

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
    sys.stdout.write(f"How many layers? [default {detected}, allowed 500-3000]: ")
    sys.stdout.flush()
    try:
        user_input = sys.stdin.readline().strip()
    except KeyboardInterrupt:
        sys.exit(1)
        
    if not user_input:
        return detected
    try:
        val = int(user_input)
        val = max(500, min(3000, val))
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

def run_cmd(exe, arguments):
    print(f"{os.path.basename(exe)} {' '.join(arguments)}")
    try:
        res = subprocess.run([exe] + arguments, cwd=os.path.dirname(exe) or None)
        return res.returncode
    except Exception as e:
        print(f"Error running command: {e}")
        return 1

def main():
    try:
        root = os.path.dirname(os.path.abspath(__file__))
        original_painter = os.path.join(root, "forza-painter.exe")
        importer = os.path.join(root, "tools", "fh6_import_layer_table.py")
        
        args = sys.argv[1:]
        if not args:
            print("Drop PNG/JPG files here to generate JSON, or drop JSON files here to import into FH6.", file=sys.stderr)
            print("FH6 JSON import requires the vinyl editor to be open with a fresh ungrouped template.", file=sys.stderr)
            input("Press Enter to close...")
            return 2
            
        exit_code = 0
        for path in args:
            layer_count = ask_layer_count(path)
            if is_json(path):
                if not os.path.exists(importer):
                    raise FileNotFoundError(f"FH6 importer not found: {importer}")
                print(f"Using FH6 target template: {layer_count} layers")
                # Run importer using current Python executable
                exit_code = run_cmd(sys.executable, [importer, path, f"--layers={layer_count}"])
            else:
                if not os.path.exists(original_painter):
                    raise FileNotFoundError(f"Original forza-painter.exe not found: {original_painter}")
                update_profiles_for_layer_count(root, layer_count)
                exit_code = run_cmd(original_painter, [path])
                
            if exit_code != 0:
                input("Press Enter to close...")
                return exit_code
                
        return exit_code
    except Exception as ex:
        print(f"ERROR: {ex}", file=sys.stderr)
        input("Press Enter to close...")
        return 1

if __name__ == "__main__":
    sys.exit(main())
