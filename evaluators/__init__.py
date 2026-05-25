#!/usr/bin/env python3
import numpy as np

# 匯入評估器抽象介面
from evaluators.base_evaluator import BaseEvaluator

# 嘗試匯入各個評估器類別，若依賴庫缺失則優雅忽略
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

from evaluators.pure_python_evaluator import PurePythonEvaluator


class EvaluatorFactory:
    @staticmethod
    def get_available_evaluators() -> list:
        """
        掃描並獲取當前環境下所有可用的運算引擎插件列表。
        每一項包含名稱、代號、是否可用以及使用的計算硬體。
        """
        evaluators = []
        
        # 1. Numba CPU JIT
        numba_avail = False
        if NumbaEvaluator is not None:
            try:
                # 測試一下 Numba JIT 的可用性
                inst = NumbaEvaluator(np.zeros((2, 2, 3), dtype=np.float32))
                numba_avail = inst.is_available()
            except Exception:
                numba_avail = False
                
        evaluators.append({
            "code": "NUMBA",
            "name": "Numba JIT (CPU Multithreading)",
            "available": numba_avail,
            "device": "CPU",
            "class": NumbaEvaluator
        })
        
        # 2. Taichi GPU Vulkan JIT
        taichi_avail = False
        if TaichiEvaluator is not None:
            try:
                inst = TaichiEvaluator(np.zeros((2, 2, 3), dtype=np.float32))
                taichi_avail = inst.is_available()
            except Exception:
                taichi_avail = False
                
        evaluators.append({
            "code": "TAICHI",
            "name": "Taichi JIT (GPU - Vulkan)",
            "available": taichi_avail,
            "device": "GPU",
            "class": TaichiEvaluator
        })
        
        # 3. Pure Python Baseline (永遠可用)
        evaluators.append({
            "code": "PURE_PYTHON",
            "name": "Pure Python (Baseline)",
            "available": True,
            "device": "CPU",
            "class": PurePythonEvaluator
        })
        
        return evaluators

    @staticmethod
    def create_evaluator(engine_name: str, target_image: np.ndarray, alpha_mask: np.ndarray = None) -> BaseEvaluator:
        """
        工廠方法：動態建立並回傳對應的評估器實例。
        核心安全性：在目標引擎不可用或載入失敗的最壞情況下，提供全自動的退級與安全回退。
        
        :param engine_name: 引擎代號 ("NUMBA", "TAICHI", "PURE_PYTHON")
        :param target_image: 目標影像矩陣
        :param alpha_mask: 目標 Alpha 遮罩
        :return: 實作 BaseEvaluator 介面的評估器對象
        """
        available_engines = EvaluatorFactory.get_available_evaluators()
        engine_map = {e["code"]: e for e in available_engines}
        
        # 預設引擎為 NUMBA (與現版本做法一致)
        selected_code = "NUMBA"
        if engine_name and engine_name.upper() in engine_map:
            selected_code = engine_name.upper()
            
        selected_engine = engine_map.get(selected_code)
        
        # 安全回退機制：如果選定的引擎不可用，嘗試依序回退
        if not selected_engine or not selected_engine["available"]:
            fallback_order = ["NUMBA", "PURE_PYTHON"]
            print(f"\n[Factory Warning] Requested engine '{selected_code}' is NOT available in this environment.")
            
            for code in fallback_order:
                if code in engine_map and engine_map[code]["available"]:
                    selected_code = code
                    selected_engine = engine_map[code]
                    print(f"[Factory Safe Fallback] Automatically falling back to available engine: '{selected_engine['name']}'")
                    break
                    
        # 取得具體的外掛類別並實例化
        eval_class = selected_engine["class"]
        
        try:
            evaluator_instance = eval_class(target_image, alpha_mask)
            print(f"[Factory Engine Load] Success! Currently powered by: {selected_engine['name']} ({selected_engine['device']})")
            return evaluator_instance
        except Exception as e:
            # 極端最壞情況：如果選取的引擎在執行個體化時又出錯，強制退回到 100% 可用的 Pure Python
            print(f"[Factory Exception] Failed to instantiate '{selected_engine['name']}': {e}")
            print(f"[Factory Absolute Safe Mode] Reverting to Pure Python (Baseline) to prevent application crash.")
            return PurePythonEvaluator(target_image, alpha_mask)
