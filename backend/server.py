import asyncio
import json
import os
import sys
import threading
import time

import websockets

# Add project root and tools path for dependencies
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "tools"))

try:
    from evaluators import EvaluatorFactory
except ImportError as e:
    print(f"Failed to import EvaluatorFactory: {e}")
    pass


class PainterServer:
    def __init__(self):
        self.clients = set()
        self.is_generating = False
        self.cancel_flag = False

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
        elif action == "start_generation":
            config = data.get("config", {})
            if not self.is_generating:
                self.generator_task = asyncio.create_task(self.start_generation(config))
        elif action == "stop_generation":
            self.cancel_flag = True
        elif action == "inject_geometry":
            config = data.get("config", {})
            asyncio.create_task(self.inject_geometry(config))

    async def broadcast(self, message):
        if self.clients:
            await asyncio.gather(*(client.send(message) for client in self.clients))

    async def broadcast_binary(self, binary_data):
        if self.clients:
            await asyncio.gather(*(client.send(binary_data) for client in self.clients))

    async def inject_geometry(self, config):
        json_path = config.get("json_path")
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

    def _sync_broadcast(self, loop, message):
        """Helper to call async broadcast from synchronous thread"""
        asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)

    def run_generator_blocking(self, config, loop):
        from tools.fh6_painter_generator import run_generator

        img_path = config.get("img_path", "")
        output_json = config.get("output_json", "")
        if not output_json:
            img_base = os.path.splitext(os.path.basename(img_path))[0]
            output_dir = os.path.join(ROOT_DIR, "output", img_base)
            output_json = os.path.join(output_dir, f"{img_base}.json")
        profile_path = config.get("profile_path", None)
        layers = config.get("layers", 1000)
        engine_code = config.get("engine_code", "NUMBA")

        # Accumulate shapes to stream Vector Renderer (will be used in deep refactoring)
        _shapes_cache = []

        def generator_cb(curr, total, speed, eta, canvas_arr, shapes_list=None):
            if self.cancel_flag:
                return False

            nonlocal _shapes_cache
            if shapes_list is not None:
                _shapes_cache = shapes_list

            msg = json.dumps(
                {
                    "action": "metrics",
                    "curr": curr,
                    "total": total,
                    "speed": speed,
                    "eta": eta,
                    "shapes": _shapes_cache,
                }
            )
            self._sync_broadcast(loop, msg)
            return True

        # Fallback settings if not provided
        opt_settings = {
            "image_pyramid": {"enabled": True},
            "importance_sampling": {"enabled": True},
            "simulated_annealing": {"enabled": True},
            "dynamic_freeze": {"enabled": True},
            "error_weighting": {"enabled": True},
            "decaying_shape": {"enabled": True},
            "early_convergence": {"enabled": False},
        }

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
                        try:
                            # arr is a numpy array (H, W, 3) RGB
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
                        progress_callback=go_progress,
                        preview_callback=go_preview,
                        on_success_callback=go_success,
                        on_failed_callback=lambda msg: print(
                            f"Go Engine Failed: {msg}"
                        ),
                    )
            else:
                res = run_generator(
                    img_path,
                    output_json,
                    profile_path,
                    layers,
                    None,
                    None,
                    generator_cb,
                    opt_settings,
                    engine_code,
                )
            if res != 0:
                self._sync_broadcast(
                    loop,
                    json.dumps({"action": "generation_status", "status": "failed"}),
                )
        except Exception as e:
            self._sync_broadcast(
                loop,
                json.dumps(
                    {"action": "generation_status", "status": "failed", "error": str(e)}
                ),
            )

    async def start_generation(self, config):
        self.is_generating = True
        self.cancel_flag = False

        await self.broadcast(
            json.dumps({"action": "generation_status", "status": "started"})
        )

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.run_generator_blocking, config, loop)

        self.is_generating = False
        if not self.cancel_flag:
            await self.broadcast(
                json.dumps({"action": "generation_status", "status": "completed"})
            )


async def main():
    server = PainterServer()
    async with websockets.serve(server.register, "localhost", 8765):
        print("FH6 Painter Backend API Server running on ws://localhost:8765")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
