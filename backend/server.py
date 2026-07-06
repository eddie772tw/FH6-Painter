import asyncio
import json
import os
import sys
import threading
import time

import websockets

# Add project root and tools path for dependencies
if getattr(sys, "frozen", False):
    ROOT_DIR = sys._MEIPASS
else:
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "tools"))

try:
    from evaluators import EvaluatorFactory
except ImportError as e:
    print(f"Failed to import EvaluatorFactory: {e}")
    pass

try:
    from utils import get_output_base_dir, scan_gpus, scan_profiles
except ImportError:
    scan_profiles = None
    scan_gpus = None

    def get_output_base_dir():
        return ROOT_DIR


def get_project_base(filepath):
    if not filepath:
        return ""
    base = os.path.splitext(os.path.basename(filepath))[0]
    if base.endswith("_masked"):
        base = base[:-7]
    if base == "_temp_resume":
        dir_name = os.path.dirname(os.path.abspath(filepath))
        parent_dir_name = os.path.basename(dir_name)
        return parent_dir_name

    # If the file is inside output/something/, the directory name is project base
    dir_name = os.path.dirname(os.path.abspath(filepath))
    parent_dir_name = os.path.basename(dir_name)
    grandparent_dir_name = os.path.basename(os.path.dirname(dir_name))
    if grandparent_dir_name.lower() == "output":
        return parent_dir_name

    import re

    # Match project base name before dot or underscore followed by numbers
    match = re.match(r"^(.+?)(?:[._]\d+)?$", base)
    if match:
        return match.group(1)
    return base


def get_image_info(image_path):
    try:
        import base64
        import io

        from PIL import Image

        with Image.open(image_path) as img:
            width, height = img.size
            preview_img = img.copy()
            preview_img.thumbnail((800, 800))
            buffer = io.BytesIO()
            if preview_img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", preview_img.size, (128, 128, 128))
                bg.paste(preview_img, mask=preview_img.split()[-1])
                preview_img = bg
            else:
                preview_img = preview_img.convert("RGB")
            preview_img.save(buffer, format="JPEG", quality=80)
            b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return {"width": width, "height": height, "preview_base64": b64}
    except Exception as e:
        print(f"Error getting image info: {e}")
        return None


class PainterServer:
    def __init__(self):
        self.clients = set()
        self.is_generating = False
        self.cancel_flag = False
        self.current_go_evaluator = None
        self.preview_enabled = True

    async def register(self, websocket):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        finally:
            self.clients.remove(websocket)

    async def handle_message(self, websocket, message):
        data = json.loads(message)
        action = data.get("action")

        if action == "ping":
            await websocket.send(json.dumps({"action": "pong"}))
        elif action == "get_engines":
            engines = []
            if "EvaluatorFactory" in globals():
                raw_engines = EvaluatorFactory.get_available_evaluators()
                for e in raw_engines:
                    clean_e = {k: v for k, v in e.items() if k != "class"}
                    engines.append(clean_e)
            try:
                await websocket.send(
                    json.dumps({"action": "engines_list", "data": engines})
                )
            except Exception as e:
                print(f"Error sending engines_list: {e}")
        elif action == "get_profiles":
            profiles_list = []
            if scan_profiles:
                try:
                    raw_profiles = scan_profiles()
                    for p in raw_profiles:
                        profiles_list.append(
                            {
                                "filename": p.get("filename", ""),
                                "name": p.get("name", ""),
                                "desc": p.get("desc", ""),
                                "path": p.get("path", ""),
                            }
                        )
                except Exception as e:
                    print(f"Error scanning profiles: {e}")
            await websocket.send(
                json.dumps({"action": "profiles_list", "data": profiles_list})
            )
        elif action == "get_gpus":
            gpus_list = []
            if scan_gpus:
                try:
                    gpus_list = scan_gpus()
                except Exception as e:
                    print(f"Error scanning GPUs: {e}")
            await websocket.send(json.dumps({"action": "gpus_list", "data": gpus_list}))
        elif action == "get_languages":
            lang_dir = os.path.join(ROOT_DIR, "lang")
            languages = []
            iso639_path = os.path.join(lang_dir, "iso639.json")
            iso639_dict = {}
            if os.path.exists(iso639_path):
                try:
                    with open(iso639_path, "r", encoding="utf-8") as f:
                        iso639_dict = json.load(f)
                except Exception as e:
                    print(f"Error loading iso639.json: {e}")

            if os.path.exists(lang_dir) and os.path.isdir(lang_dir):
                try:
                    for filename in os.listdir(lang_dir):
                        if filename.endswith(".json") and filename != "iso639.json":
                            code = filename[:-5]
                            name = iso639_dict.get(code, code)
                            languages.append({"code": code, "name": name})
                except Exception as e:
                    print(f"Error scanning lang directory: {e}")

            languages.sort(key=lambda x: x["code"])
            await websocket.send(
                json.dumps({"action": "languages_list", "data": languages})
            )
        elif action == "get_lang":
            lang_code = data.get("lang", "en-us")
            lang_path = os.path.join(ROOT_DIR, "lang", f"{lang_code}.json")
            try:
                with open(lang_path, "r", encoding="utf-8") as f:
                    lang_data = json.load(f)
                await websocket.send(
                    json.dumps({"action": "lang_data", "data": lang_data})
                )
            except Exception as e:
                print(f"Error loading lang {lang_code}: {e}")
        elif action == "get_profile_settings":
            profile_name = data.get("profile_name", "")
            settings_dir = os.path.join(ROOT_DIR, "settings")
            profile_path = os.path.join(settings_dir, f"{profile_name}.ini")

            stopAt, randomSamples, mutatedSamples, desc = (
                "2000",
                "20000",
                "200",
                "No description available.",
            )
            if os.path.exists(profile_path):
                try:
                    from tools.fh6_painter_generator import load_profile

                    params = load_profile(profile_path)
                    stopAt = params.get("stopAt", "2000")
                    randomSamples = params.get("randomSamples", "20000")
                    mutatedSamples = params.get("mutatedSamples", "200")

                    with open(profile_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip().startswith("description"):
                                parts = line.split("=", 1)
                                if len(parts) == 2:
                                    desc = parts[1].strip()
                                break
                except Exception as e:
                    print(f"Error loading profile settings: {e}")
            await websocket.send(
                json.dumps(
                    {
                        "action": "profile_settings",
                        "profile_name": profile_name,
                        "settings": {
                            "stopAt": stopAt,
                            "randomSamples": randomSamples,
                            "mutatedSamples": mutatedSamples,
                            "description": desc,
                        },
                    }
                )
            )
        elif action == "get_checkpoints":
            img_path = data.get("img_path", "")
            checkpoints = {}
            if img_path:
                img_base = get_project_base(img_path)
                if img_base:
                    output_dir = os.path.join(get_output_base_dir(), "output", img_base)
                    if os.path.exists(output_dir):
                        import glob

                        for f in glob.glob(
                            os.path.join(output_dir, f"{img_base}_*.json")
                        ) + glob.glob(os.path.join(output_dir, f"{img_base}.*.json")):
                            basename = os.path.basename(f)
                            num_str = (
                                basename.replace(img_base + "_", "")
                                .replace(img_base + ".", "")
                                .replace(".json", "")
                            )
                            try:
                                num = int(num_str)
                                checkpoints[num] = os.path.abspath(f)
                            except Exception:
                                pass
                        # Also check for the final completed JSON file (without _<layer> suffix)
                        final_json = os.path.join(output_dir, f"{img_base}.json")
                        if os.path.exists(final_json):
                            try:
                                with open(final_json, "r", encoding="utf-8") as f:
                                    json_data = json.load(f)
                                num_layers = max(
                                    0, len(json_data.get("shapes", [])) - 1
                                )
                                if num_layers > 0:
                                    checkpoints[num_layers] = os.path.abspath(
                                        final_json
                                    )
                            except Exception:
                                pass
                if img_path.lower().endswith(".json") and os.path.exists(img_path):
                    # Do not add temporary resume file to checkpoints list
                    if not os.path.basename(img_path).startswith("_temp_resume"):
                        try:
                            with open(img_path, "r", encoding="utf-8") as f:
                                json_data = json.load(f)
                            num_layers = max(0, len(json_data.get("shapes", [])) - 1)
                            if num_layers > 0:
                                checkpoints[num_layers] = os.path.abspath(img_path)
                        except Exception:
                            pass
            sorted_cps = [
                {"layer": k, "path": v} for k, v in sorted(checkpoints.items())
            ]
            await websocket.send(
                json.dumps({"action": "checkpoints_list", "checkpoints": sorted_cps})
            )
        elif action == "rewind_checkpoint":
            filepath = data.get("path", "")
            slice_layer = data.get("layer", 1)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                shapes = json_data.get("shapes", [])
                sliced_shapes = shapes[: slice_layer + 1]

                project_base = get_project_base(filepath)
                temp_dir = os.path.join(get_output_base_dir(), "output", project_base)
                os.makedirs(temp_dir, exist_ok=True)
                temp_path = os.path.join(temp_dir, "_temp_resume.json")

                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump({"shapes": sliced_shapes}, f)

                header = shapes[0] if len(shapes) > 0 else {}
                h_data = header.get("data", [0.0, 0.0, 600.0, 600.0])
                h_color = header.get("color", [128, 128, 128, 0])
                width = int(h_data[2]) if len(h_data) >= 3 else 600
                height = int(h_data[3]) if len(h_data) >= 4 else 600
                avg_r, avg_g, avg_b = h_color[0], h_color[1], h_color[2]

                import copy

                import numpy as np

                from tools.fh6_painter_generator import scale_shapes_list

                render_scale = 2.0
                width_high = int(width * render_scale)
                height_high = int(height * render_scale)
                shapes_copied = copy.deepcopy(sliced_shapes)
                scale_shapes_list(shapes_copied, render_scale)

                canvas_arr = np.zeros((height_high, width_high, 4), dtype=np.float32)
                evaluator = EvaluatorFactory.create_evaluator(
                    "NUMBA",
                    np.zeros((height_high, width_high, 3), dtype=np.float32),
                    None,
                )
                evaluator.rebuild_canvas(canvas_arr, shapes_copied, avg_r, avg_g, avg_b)
                evaluator.cleanup()

                import base64
                import io

                from PIL import Image

                rgb_arr = canvas_arr[:, :, :3].astype(np.uint8)
                img = Image.fromarray(rgb_arr, "RGB")
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

                await websocket.send(
                    json.dumps(
                        {
                            "action": "rewind_success",
                            "temp_path": os.path.abspath(temp_path),
                            "layer": slice_layer,
                            "preview_base64": b64,
                            "shapes": sliced_shapes,
                            "width": width,
                            "height": height,
                        }
                    )
                )
            except Exception as e:
                await websocket.send(
                    json.dumps({"action": "rewind_failed", "error": str(e)})
                )
        elif action == "load_json_file":
            filepath = data.get("path", "")
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                shapes = json_data.get("shapes", [])

                header = shapes[0] if len(shapes) > 0 else {}
                h_data = header.get("data", [0.0, 0.0, 600.0, 600.0])
                h_color = header.get("color", [128, 128, 128, 0])
                width = int(h_data[2]) if len(h_data) >= 3 else 600
                height = int(h_data[3]) if len(h_data) >= 4 else 600
                avg_r, avg_g, avg_b = h_color[0], h_color[1], h_color[2]

                import copy

                import numpy as np

                from tools.fh6_painter_generator import scale_shapes_list

                render_scale = 2.0
                width_high = int(width * render_scale)
                height_high = int(height * render_scale)
                shapes_copied = copy.deepcopy(shapes)
                scale_shapes_list(shapes_copied, render_scale)

                canvas_arr = np.zeros((height_high, width_high, 4), dtype=np.float32)
                evaluator = EvaluatorFactory.create_evaluator(
                    "NUMBA",
                    np.zeros((height_high, width_high, 3), dtype=np.float32),
                    None,
                )
                evaluator.rebuild_canvas(canvas_arr, shapes_copied, avg_r, avg_g, avg_b)
                evaluator.cleanup()

                import base64
                import io

                from PIL import Image

                rgb_arr = canvas_arr[:, :, :3].astype(np.uint8)
                img = Image.fromarray(rgb_arr, "RGB")
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

                await websocket.send(
                    json.dumps(
                        {
                            "action": "load_json_success",
                            "path": os.path.abspath(filepath),
                            "shapes": shapes,
                            "preview_base64": b64,
                            "width": width,
                            "height": height,
                        }
                    )
                )
            except Exception as e:
                await websocket.send(
                    json.dumps({"action": "load_json_failed", "error": str(e)})
                )
        elif action == "load_image_file":
            filepath = data.get("path", "")
            try:
                info = get_image_info(filepath)
                if info:
                    await websocket.send(
                        json.dumps(
                            {
                                "action": "load_image_success",
                                "path": os.path.abspath(filepath),
                                "width": info["width"],
                                "height": info["height"],
                                "preview_base64": info["preview_base64"],
                            }
                        )
                    )
                else:
                    raise Exception("Failed to read image info")
            except Exception as e:
                await websocket.send(
                    json.dumps({"action": "load_image_failed", "error": str(e)})
                )
        elif action == "browse_file":
            try:
                import tkinter as tk
                from tkinter import filedialog

                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                file_path = filedialog.askopenfilename(
                    title="Select Image or JSON File",
                    filetypes=[
                        (
                            "Supported Files (*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.json)",
                            "*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.json",
                        ),
                        (
                            "Images (*.png;*.jpg;*.jpeg;*.bmp;*.webp)",
                            "*.png;*.jpg;*.jpeg;*.bmp;*.webp",
                        ),
                        ("Geometry JSON (*.json)", "*.json"),
                        ("All files (*.*)", "*.*"),
                    ],
                )
                root.destroy()
                if file_path:
                    file_path = os.path.abspath(file_path)
                await websocket.send(
                    json.dumps({"action": "file_selected", "path": file_path})
                )
            except Exception as e:
                print(f"Error opening file dialog: {e}")
                await websocket.send(
                    json.dumps({"action": "file_selected", "path": "", "error": str(e)})
                )
        elif action == "start_generation":
            config = data.get("config", {})
            if not self.is_generating:
                self.generator_task = asyncio.create_task(self.start_generation(config))
        elif action == "stop_generation":
            self.cancel_flag = True
            go_eval = getattr(self, "current_go_evaluator", None)
            if go_eval:
                try:
                    go_eval.stop_generator()
                except Exception as e:
                    print(f"Error stopping Go evaluator: {e}")
        elif action == "inject_geometry":
            config = data.get("config", {})
            asyncio.create_task(self.inject_geometry(config))
        elif action == "generate_text_vinyl":
            text_val = data.get("text", "")
            font_size = data.get("font_size", 72)
            out_path = os.path.join(get_output_base_dir(), "output", "text_vinyl.json")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            try:
                from tools.text_generator import save_text_json

                save_text_json(text_val, "arial.ttf", font_size, out_path)
                await websocket.send(
                    json.dumps(
                        {
                            "action": "text_vinyl_success",
                            "path": os.path.abspath(out_path),
                        }
                    )
                )
            except Exception as e:
                await websocket.send(
                    json.dumps(
                        {"action": "log", "text": f"Text Vinyl Error: {str(e)}\n"}
                    )
                )
        elif action == "start_benchmark":
            asyncio.create_task(self.run_benchmark())
        elif action == "set_preview":
            self.preview_enabled = data.get("enabled", True)
        elif action == "open_output":
            try:
                output_dir = os.path.join(get_output_base_dir(), "output")
                os.makedirs(output_dir, exist_ok=True)
                if os.name == "nt":
                    os.startfile(output_dir)
                else:
                    import subprocess

                    subprocess.Popen(["xdg-open", output_dir])
            except Exception as e:
                print(f"Failed to open output directory: {e}")
        elif action == "open_url":
            try:
                import webbrowser

                url = data.get("url")
                if url:
                    webbrowser.open(url)
            except Exception as e:
                print(f"Failed to open URL: {e}")

    async def broadcast(self, message):
        if self.clients:
            await asyncio.gather(*(client.send(message) for client in self.clients))

    async def broadcast_binary(self, binary_data):
        if self.clients:
            await asyncio.gather(*(client.send(binary_data) for client in self.clients))

    async def inject_geometry(self, config):
        img_path = config.get("json_path", "")

        # Reconstruct the expected JSON path from the original image filename
        img_base = get_project_base(img_path)
        output_dir = os.path.join(get_output_base_dir(), "output", img_base)
        json_path = os.path.join(output_dir, f"{img_base}.json")

        layers = config.get("layers", 3000)

        await self.broadcast(
            json.dumps({"action": "injection_status", "status": "started"})
        )

        try:
            from tools.fh6_import_layer_table import run_importer

            loop = asyncio.get_running_loop()
            # run_importer blocks, use thread executor
            result = await loop.run_in_executor(
                None,
                run_importer,
                json_path,
                layers,
                False,
                False,
                False,
                False,
                63.0,
                1.0,
                200000,
            )

            if result == 0:
                await self.broadcast(
                    json.dumps({"action": "injection_status", "status": "completed"})
                )
            else:
                await self.broadcast(
                    json.dumps(
                        {
                            "action": "injection_status",
                            "status": "failed",
                            "error": f"Exit code {result}",
                        }
                    )
                )
        except Exception as e:
            await self.broadcast(
                json.dumps(
                    {"action": "injection_status", "status": "failed", "error": str(e)}
                )
            )

    async def run_benchmark(self):
        script_path = os.path.join(ROOT_DIR, "tools", "benchmark", "__main__.py")
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode("utf-8", errors="replace").rstrip()
                await self.broadcast(
                    json.dumps({"action": "benchmark_log", "text": decoded_line + "\n"})
                )

            await process.wait()
            status = "PASSED" if process.returncode == 0 else "FAILED"
            await self.broadcast(
                json.dumps({"action": "benchmark_done", "status": status})
            )
        except Exception as e:
            await self.broadcast(
                json.dumps(
                    {
                        "action": "benchmark_log",
                        "text": f"Error starting benchmark: {str(e)}\n",
                    }
                )
            )
            await self.broadcast(
                json.dumps({"action": "benchmark_done", "status": "FAILED"})
            )

    def _sync_broadcast(self, loop, message):
        """Helper to call async broadcast from synchronous thread"""
        asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)

    def run_generator_blocking(self, config, loop):
        from tools.fh6_painter_generator import run_generator

        img_path = config.get("img_path", "")

        # Resolve resume path
        resume_path = config.get("resume_path", None)
        if img_path.lower().endswith(".json"):
            resume_path = img_path
            original_img_path = config.get("original_img_path", "")
            if original_img_path and os.path.exists(original_img_path):
                img_path = original_img_path
            else:
                json_base = get_project_base(img_path)

                found_img = None
                if json_base:
                    import glob

                    # Check output folder first, then the directory of img_path
                    for json_dir in [
                        os.path.join(get_output_base_dir(), "output", json_base),
                        os.path.dirname(img_path),
                    ]:
                        for img_ext in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]:
                            candidates = glob.glob(
                                os.path.join(json_dir, f"{json_base}*{img_ext}")
                            )
                            # Filter out masked images to prevent lingering bounds
                            candidates = [
                                c
                                for c in candidates
                                if not c.endswith(f"_masked{img_ext}")
                            ]
                            if candidates:
                                found_img = candidates[0]
                                break
                        if found_img:
                            break
                if found_img:
                    img_path = found_img

        # Copy original image to output folder
        if (
            img_path
            and not img_path.lower().endswith(".json")
            and os.path.exists(img_path)
        ):
            try:
                img_base = get_project_base(img_path)
                output_dir = os.path.join(get_output_base_dir(), "output", img_base)
                os.makedirs(output_dir, exist_ok=True)
                dest_img_path = os.path.join(output_dir, os.path.basename(img_path))
                if os.path.abspath(img_path) != os.path.abspath(dest_img_path):
                    import shutil

                    shutil.copy2(img_path, dest_img_path)
                    img_path = dest_img_path
            except Exception as e:
                print(f"[Warning] Failed to copy original image to output: {e}")

        original_target_image_path = img_path

        # Apply Region Mask (Alpha Masking) if ROI is defined and enabled
        roi_config = config.get("roi", {})
        roi_min_layers = roi_config.get("min_layers", 500)

        current_layer = 0
        if config.get("resume_path") and os.path.exists(config["resume_path"]):
            try:
                with open(config["resume_path"], "r", encoding="utf-8") as f:
                    j = json.load(f)
                    current_layer = max(0, len(j.get("shapes", [])) - 1)
            except Exception:
                pass

        original_target_layers = config.get("layers", 1000)
        pending_roi_phase2 = False

        if (
            roi_config.get("enabled", False)
            and img_path
            and not img_path.lower().endswith(".json")
            and os.path.exists(img_path)
        ):
            if current_layer < roi_min_layers:
                print(
                    f"[System] 目前總圖層數 ({current_layer}) 小於區域繪製要求的最少輪廓層數 ({roi_min_layers})。本次生成將強制採用全圖生成以建立初步輪廓。"
                )
                if original_target_layers > roi_min_layers:
                    pending_roi_phase2 = True
                    config["layers"] = roi_min_layers
            else:
                try:
                    import numpy as np
                    from PIL import Image

                    with Image.open(img_path) as src_img:
                        src_img = src_img.convert("RGBA")
                        arr = np.array(src_img)

                        cw = roi_config.get("canvas_w", arr.shape[1])
                        ch = roi_config.get("canvas_h", arr.shape[0])
                        scale_x = arr.shape[1] / cw if cw > 0 else 1.0
                        scale_y = arr.shape[0] / ch if ch > 0 else 1.0

                        rx1 = int(roi_config.get("x1", 0) * scale_x)
                        ry1 = int(roi_config.get("y1", 0) * scale_y)
                        rx2 = int(roi_config.get("x2", arr.shape[1] - 1) * scale_x)
                        ry2 = int(roi_config.get("y2", arr.shape[0] - 1) * scale_y)

                        rx1 = max(0, min(rx1, arr.shape[1] - 1))
                        rx2 = max(0, min(rx2, arr.shape[1] - 1))
                        ry1 = max(0, min(ry1, arr.shape[0] - 1))
                        ry2 = max(0, min(ry2, arr.shape[0] - 1))

                        x_min, x_max = min(rx1, rx2), max(rx1, rx2)
                        y_min, y_max = min(ry1, ry2), max(ry1, ry2)

                        alpha_mask = np.zeros(
                            (arr.shape[0], arr.shape[1]), dtype=np.uint8
                        )
                        shape_mode = roi_config.get("shape", "rectangle")

                        if shape_mode == "ellipse":
                            center_x = (x_min + x_max) / 2.0
                            center_y = (y_min + y_max) / 2.0
                            radius_x = (x_max - x_min) / 2.0
                            radius_y = (y_max - y_min) / 2.0
                            if radius_x > 0 and radius_y > 0:
                                yy, xx = np.ogrid[: arr.shape[0], : arr.shape[1]]
                                ellipse_dist = ((xx - center_x) / radius_x) ** 2 + (
                                    (yy - center_y) / radius_y
                                ) ** 2
                                alpha_mask[ellipse_dist <= 1.0] = 255
                        else:
                            alpha_mask[y_min : y_max + 1, x_min : x_max + 1] = 255

                        arr[:, :, 3] = np.minimum(arr[:, :, 3], alpha_mask)

                        masked_img = Image.fromarray(arr)
                        img_base = get_project_base(img_path)
                        output_dir = os.path.join(
                            get_output_base_dir(), "output", img_base
                        )
                        os.makedirs(output_dir, exist_ok=True)
                        masked_path = os.path.join(output_dir, f"{img_base}_masked.png")
                        masked_img.save(masked_path)
                        img_path = masked_path
                        print(f"[Region Mask] Mask applied. Path: {img_path}")
                except Exception as e:
                    print(f"Error applying ROI mask: {e}")

        output_json = config.get("output_json", "")
        if not output_json and img_path:
            img_base = get_project_base(img_path)
            output_dir = os.path.join(get_output_base_dir(), "output", img_base)
            output_json = os.path.join(output_dir, f"{img_base}.json")

        profile_path = config.get("profile_path", None)
        if not profile_path and config.get("profile_name"):
            profile_path = os.path.join(
                ROOT_DIR, "settings", f"{config.get('profile_name')}.ini"
            )
        if not profile_path:
            profile_path = os.path.join(
                ROOT_DIR, "settings", "c. balanced - good quality and speed.ini"
            )

        layers = config.get("layers", 1000)
        engine_code = config.get("engine_code", "NUMBA")
        taichi_arch = config.get("taichi_arch", "Vulkan")
        taichi_device_id = config.get("taichi_device_id", 0)
        use_pure_gpu = config.get("use_pure_gpu", False)
        candidates_limit = config.get("candidates_limit", None)
        steps_limit = config.get("steps_limit", None)

        _shapes_cache = []

        def generator_cb(curr, total, speed, eta, canvas_arr, shapes_list=None):
            if self.cancel_flag:
                return False

            nonlocal _shapes_cache
            if shapes_list is not None:
                _shapes_cache = shapes_list

            h, w = canvas_arr.shape[:2]

            msg = json.dumps(
                {
                    "action": "metrics",
                    "curr": curr,
                    "total": total,
                    "speed": speed,
                    "slate": 0.0,
                    "eta": eta,
                    "shapes": _shapes_cache,
                    "width": w,
                    "height": h,
                }
            )
            self._sync_broadcast(loop, msg)

            return True

        # Read optimization settings
        opt_settings = config.get(
            "opt_settings",
            {
                "image_pyramid": {"enabled": True},
                "importance_sampling": {"enabled": True},
                "simulated_annealing": {"enabled": True},
                "dynamic_freeze": {"enabled": True},
                "error_weighting": {"enabled": True},
                "decaying_shape": {"enabled": True},
                "early_convergence": {"enabled": False},
            },
        )
        # Sync early convergence check
        if "early_convergence" not in opt_settings:
            opt_settings["early_convergence"] = {}
        opt_settings["early_convergence"]["enabled"] = config.get(
            "early_convergence", False
        )
        opt_settings["roi_enabled"] = config.get("roi", {}).get("enabled", False)

        try:
            if engine_code == "GO_OPENCL":
                import base64
                import io

                import numpy as np
                from PIL import Image

                from evaluators import EvaluatorFactory

                eval_cls = None
                for e in EvaluatorFactory.get_available_evaluators():
                    if e["code"] == "GO_OPENCL":
                        eval_cls = e["class"]
                        break

                if eval_cls:
                    evaluator = eval_cls(np.zeros((2, 2, 3), dtype=np.float32))
                    self.current_go_evaluator = evaluator

                    def go_progress(curr, total, speed, eta):
                        if self.cancel_flag:
                            evaluator.cancel_flag = True
                        msg = json.dumps(
                            {
                                "action": "metrics",
                                "curr": curr,
                                "total": total,
                                "speed": speed,
                                "eta": eta,
                                "shapes": [],
                            }
                        )
                        self._sync_broadcast(loop, msg)

                    def go_preview(arr):
                        if self.cancel_flag:
                            return
                        if not getattr(self, "preview_enabled", True):
                            return
                        try:
                            img = Image.fromarray(arr.astype("uint8"), "RGB")
                            buffer = io.BytesIO()
                            img.save(buffer, format="JPEG", quality=85)
                            b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                            msg = json.dumps(
                                {"action": "pixel_preview", "image_base64": b64}
                            )
                            self._sync_broadcast(loop, msg)
                        except Exception as e:
                            print(f"Error sending preview: {e}")

                    def go_success():
                        try:
                            if os.path.exists(output_json):
                                with open(output_json, "r", encoding="utf-8") as f:
                                    res = json.load(f)
                                    if "shapes" in res:
                                        msg = json.dumps(
                                            {
                                                "action": "metrics",
                                                "curr": layers,
                                                "total": layers,
                                                "speed": 0.0,
                                                "eta": 0.0,
                                                "shapes": res["shapes"],
                                            }
                                        )
                                        self._sync_broadcast(loop, msg)
                        except Exception as e:
                            print(f"Failed to read final Go JSON: {e}")

                    res = evaluator.run_generator(
                        img_path=img_path,
                        output_json=output_json,
                        profile_path=profile_path,
                        layers=layers,
                        resume_path=resume_path,
                        progress_callback=go_progress,
                        preview_callback=go_preview,
                        on_success_callback=go_success,
                        on_failed_callback=lambda msg: print(
                            f"Go Engine Failed: {msg}"
                        ),
                    )
            else:
                res = run_generator(
                    image_path=img_path,
                    output_path=output_json,
                    profile_path=profile_path,
                    layers_limit=layers,
                    candidates_limit=candidates_limit,
                    steps_limit=steps_limit,
                    progress_callback=generator_cb,
                    opt_settings=opt_settings,
                    engine_name=engine_code,
                    taichi_arch=taichi_arch,
                    taichi_device_id=taichi_device_id,
                    use_pure_gpu=use_pure_gpu,
                    resume_path=resume_path,
                )
            if res != 0:
                self._sync_broadcast(
                    loop,
                    json.dumps({"action": "generation_status", "status": "failed"}),
                )
            elif pending_roi_phase2 and not self.cancel_flag:
                print(
                    f"[System] 建立初步輪廓 ({roi_min_layers} 層) 完成，將自動重啟並套用區域繪製進行後續生成。"
                )
                config["layers"] = original_target_layers
                config["resume_path"] = output_json
                config["img_path"] = original_target_image_path
                return self.run_generator_blocking(config, loop)

        except Exception as e:
            if str(e) == "EARLY_CONVERGENCE_WITH_ROI":
                if self.cancel_flag:
                    return
                self._sync_broadcast(loop, json.dumps({"action": "clear_roi"}))
                if "roi" in config:
                    config["roi"]["enabled"] = False
                config["img_path"] = original_target_image_path
                config["resume_path"] = output_json
                return self.run_generator_blocking(config, loop)

            self._sync_broadcast(
                loop,
                json.dumps(
                    {"action": "generation_status", "status": "failed", "error": str(e)}
                ),
            )
        finally:
            self.current_go_evaluator = None

    async def start_generation(self, config):
        self.is_generating = True
        self.cancel_flag = False

        await self.broadcast(
            json.dumps({"action": "generation_status", "status": "started"})
        )

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.run_generator_blocking, config, loop)

        self.is_generating = False
        status_str = "completed" if not self.cancel_flag else "stopped"
        await self.broadcast(
            json.dumps({"action": "generation_status", "status": status_str})
        )


def check_parent_alive():
    try:
        sys.stdin.read()
    except Exception:
        pass
    print("Parent process disconnected. Exiting sidecar.")
    os._exit(0)


def check_frontend_alive(proc):
    proc.wait()
    print("Frontend process exited. Exiting backend.")
    os._exit(0)


class BroadcastLogger:
    def __init__(self, original_stream, server_instance, loop):
        self.original_stream = original_stream
        self.server = server_instance
        self.loop = loop

    def write(self, message):
        if self.original_stream:
            try:
                self.original_stream.write(message)
                self.original_stream.flush()
            except Exception:
                pass
        if message.strip():
            try:
                msg = json.dumps({"action": "log", "text": message})
                self.server._sync_broadcast(self.loop, msg)
            except Exception:
                pass

    def flush(self):
        if self.original_stream:
            try:
                self.original_stream.flush()
            except Exception:
                pass


async def main():
    if getattr(sys, "frozen", False):
        frontend_path = os.path.join(sys._MEIPASS, "frontend.exe")
        if os.path.exists(frontend_path):
            import subprocess

            proc = subprocess.Popen([frontend_path, "--no-sidecar"])
            threading.Thread(
                target=check_frontend_alive, args=(proc,), daemon=True
            ).start()
        else:
            print("Frontend executable not found in bundle!")
    else:
        pass  # Disabling check_parent_alive for local script environments if stdin is non-interactive but not launched from bundle

    server = PainterServer()
    loop = asyncio.get_running_loop()

    # Redirect stdout and stderr to broadcast to frontend
    sys.stdout = BroadcastLogger(sys.stdout, server, loop)
    sys.stderr = BroadcastLogger(sys.stderr, server, loop)

    async with websockets.serve(server.register, "localhost", 8765):
        print("FH6 Painter Backend API Server running on ws://localhost:8765\n")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
