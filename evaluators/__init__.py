#!/usr/bin/env python3
import numpy as np

from evaluators.base_evaluator import BaseEvaluator

HAS_NUMBA = False
try:
    from evaluators.numba_evaluator import NumbaEvaluator

    HAS_NUMBA = True
except ImportError:
    NumbaEvaluator = None

try:
    from evaluators.taichi_evaluator import TaichiEvaluator
except ImportError:
    TaichiEvaluator = None

try:
    from evaluators.cmaes_evaluator import CmaesEvaluator
except ImportError:
    CmaesEvaluator = None

try:
    from evaluators.taichi_pso_evaluator import TaichiPsoEvaluator
except ImportError:
    TaichiPsoEvaluator = None

try:
    from evaluators.pytorch_diff_evaluator import PyTorchDiffEvaluator
except ImportError:
    PyTorchDiffEvaluator = None

from evaluators.pure_python_evaluator import PurePythonEvaluator


class EvaluatorFactory:
    @staticmethod
    def get_available_evaluators() -> list:
        """掃描並獲取當前環境下所有可用的運算引擎插件列表。
        每一項包含名稱、代號、是否可用以及使用的計算硬體。
        """
        evaluators = []

        numba_avail = False
        if NumbaEvaluator is not None:
            try:
                inst = NumbaEvaluator(np.zeros((2, 2, 3), dtype=np.float32))
                numba_avail = inst.is_available()
            except Exception:
                numba_avail = False

        evaluators.append(
            {
                "code": "NUMBA",
                "name": "Numba JIT (CPU, Recommanded)",
                "available": numba_avail,
                "device": "CPU",
                "class": NumbaEvaluator,
            }
        )

        import sys

        # Disable Taichi JIT on Python 3.14+ due to lack of cp314 wheels on PyPI
        is_python_314_or_newer = sys.version_info >= (3, 14)

        from evaluators.taichi_evaluator import HAS_TAICHI

        taichi_avail = HAS_TAICHI and not is_python_314_or_newer

        evaluators.append(
            {
                "code": "TAICHI",
                "name": "Taichi JIT (GPU)",
                "available": taichi_avail,
                "device": "GPU",
                "class": TaichiEvaluator,
            }
        )

        evaluators.append(
            {
                "code": "PURE_PYTHON",
                "name": "Pure Python (Slow, for Compatiblity)",
                "available": True,
                "device": "CPU",
                "class": PurePythonEvaluator,
            }
        )

        # 註冊 CMA-ES 進化搜索引擎 (Hybrid JIT)
        cmaes_avail = False
        if CmaesEvaluator is not None:
            try:
                inst = CmaesEvaluator(np.zeros((2, 2, 3), dtype=np.float32))
                cmaes_avail = inst.is_available()
            except Exception:
                cmaes_avail = False

        evaluators.append(
            {
                "code": "CMAES_SOLVER",
                "name": "CMA-ES Solver Engine (Hybrid JIT)",
                "available": cmaes_avail,
                "device": "CPU",
                "class": CmaesEvaluator,
            }
        )

        # 註冊 Taichi GPU 粒子群優化 (PSO) 引擎
        taichi_pso_avail = False
        if TaichiPsoEvaluator is not None:
            try:
                # 重複使用 Python 3.14+ 禁用邏輯
                if not is_python_314_or_newer:
                    inst = TaichiPsoEvaluator(np.zeros((2, 2, 3), dtype=np.float32))
                    taichi_pso_avail = inst.is_available()
            except Exception:
                taichi_pso_avail = False

        evaluators.append(
            {
                "code": "TAICHI_PSO",
                "name": "Taichi GPU Particle Swarm Optimization (PSO)",
                "available": taichi_pso_avail,
                "device": "GPU",
                "class": TaichiPsoEvaluator,
            }
        )

        # 註冊 PyTorch 可微渲染器 (Adam) 引擎
        pytorch_diff_avail = False
        if PyTorchDiffEvaluator is not None:
            try:
                inst = PyTorchDiffEvaluator(np.zeros((2, 2, 3), dtype=np.float32))
                pytorch_diff_avail = inst.is_available()
            except Exception:
                pytorch_diff_avail = False

        evaluators.append(
            {
                "code": "PYTORCH_DIFF",
                "name": "PyTorch Differentiable Renderer (GPU Adam)",
                "available": pytorch_diff_avail,
                "device": "GPU",
                "class": PyTorchDiffEvaluator,
            }
        )

        return evaluators

    @staticmethod
    def create_evaluator(
        engine_name: str,
        target_image: np.ndarray,
        alpha_mask: np.ndarray = None,
        **kwargs,
    ) -> BaseEvaluator:
        available_engines = EvaluatorFactory.get_available_evaluators()
        engine_map = {e["code"]: e for e in available_engines}

        selected_code = "NUMBA"
        if engine_name and engine_name.upper() in engine_map:
            selected_code = engine_name.upper()

        selected_engine = engine_map.get(selected_code)

        if not selected_engine or not selected_engine["available"]:
            fallback_order = ["NUMBA", "PURE_PYTHON"]
            print(
                f"\n[Factory Warning] Requested engine '{selected_code}' is NOT available in this environment."
            )

            for code in fallback_order:
                if code in engine_map and engine_map[code]["available"]:
                    selected_code = code
                    selected_engine = engine_map[code]
                    print(
                        f"[Factory Safe Fallback] Automatically falling back to available engine: '{selected_engine['name']}'"
                    )
                    break

        eval_class = selected_engine["class"]

        try:
            evaluator_instance = None
            if selected_code in ("TAICHI", "TAICHI_PSO"):
                evaluator_instance = eval_class(target_image, alpha_mask, **kwargs)
            else:
                evaluator_instance = eval_class(target_image, alpha_mask)
            print(
                f"[Factory Engine Load] Success! Currently powered by: {selected_engine['name']} ({selected_engine['device']})"
            )
            return evaluator_instance
        except Exception as e:
            print(
                f"[Factory Exception] Failed to instantiate '{selected_engine['name']}': {e}"
            )
            print(
                "[Factory Absolute Safe Mode] Reverting to Pure Python (Baseline) to prevent application crash."
            )
            return PurePythonEvaluator(target_image, alpha_mask)
