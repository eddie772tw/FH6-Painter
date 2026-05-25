#!/usr/bin/env python3
import sys
import os
import time
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import taichi as ti
    HAS_TAICHI = True
except ImportError:
    HAS_TAICHI = False

try:
    import numba
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False

try:
    from PIL import Image
except ImportError:
    print("ERROR: Please install pillow to run the benchmark script: pip install pillow")
    sys.exit(1)

from evaluators.taichi_evaluator import TaichiEvaluator
from evaluators.numba_evaluator import NumbaEvaluator

def benchmark_for_resolution(res_w, res_h):
    print(f"\n======================================================================")
    print(f"                {res_w} x {res_h} Benchmark")
    print(f"======================================================================")
    

    target_img = np.random.rand(res_h, res_w, 3).astype(np.float32) * 255.0
    current_canvas = np.zeros_like(target_img)
    

    batch_size = 20000
    optimization_steps = 50
    params = {
        "current_max_r": min(res_w, res_h) / 3.0,
        "use_importance": True,
        "error_prob": np.ones((res_h, res_w), dtype=np.float32),
        "use_freeze": True,
        "freeze_mask": np.zeros((res_h, res_w), dtype=np.uint8),
        "use_weight": True,
        "weight_map": np.ones((res_h, res_w), dtype=np.float32),
        "use_uncovered": True,
        "uncovered_map": np.ones((res_h, res_w), dtype=np.float32),
        "sa_enabled": True,
        "sa_initial_temp": 5000.0,
        "sa_cooling_rate": 0.95,
        "optimization_steps": optimization_steps
    }
    
    # A. TaichiEvaluator (Vulkan + Numba hybrid)
    taichi_eval = None
    taichi_exec = 9999.0
    if HAS_TAICHI:
        try:
            taichi_eval = TaichiEvaluator(target_img, taichi_arch="Vulkan")
            if not taichi_eval.is_available():
                taichi_eval = TaichiEvaluator(target_img)
                
            if taichi_eval.is_available():
                # Warm-up
                mixed_params = params.copy()
                mixed_params["use_pure_gpu"] = False
                taichi_eval.search_best_shape(current_canvas, batch_size, mixed_params)
                ti.sync()
                

                run_count = 10
                t_start = time.perf_counter()
                for _ in range(run_count):
                    taichi_eval.search_best_shape(current_canvas, batch_size, mixed_params)
                ti.sync()
                taichi_exec = (time.perf_counter() - t_start) / run_count
        except Exception as e:
            print(f"[Taichi hybrid test error]: {e}")
            
    # B. TaichiEvaluator (pure GPU pipeline)
    taichi_pure_gpu_exec = 9999.0
    if HAS_TAICHI and taichi_eval and taichi_eval.is_available():
        try:
            # Warm-up
            pure_params = params.copy()
            pure_params["use_pure_gpu"] = True
            taichi_eval.search_best_shape(current_canvas, batch_size, pure_params)
            ti.sync()
            

            run_count = 10
            t_start = time.perf_counter()
            for _ in range(run_count):
                taichi_eval.search_best_shape(current_canvas, batch_size, pure_params)
            ti.sync()
            taichi_pure_gpu_exec = (time.perf_counter() - t_start) / run_count
        except Exception as e:
            print(f"[Taichi pure GPU test error]: {e}")
            
    # C. NumbaEvaluator
    numba_eval = None
    numba_exec = 9999.0
    if HAS_NUMBA:
        try:
            numba_eval = NumbaEvaluator(target_img)
            if numba_eval.is_available():
                # Warm-up
                numba_eval.search_best_shape(current_canvas, batch_size, params)
                

                run_count = 10
                t_start = time.perf_counter()
                for _ in range(run_count):
                    numba_eval.search_best_shape(current_canvas, batch_size, params)
                numba_exec = (time.perf_counter() - t_start) / run_count
        except Exception as e:
            print(f"[Numba test error]: {e}")
            
    print(f"\n[Results] - {res_w}x{res_h}:")
    
    if taichi_eval and taichi_eval.is_available():
        print(f"  - Taichi JIT (Vulkan + Numba hybrid): {taichi_exec*1000:.2f} ms/shape ({1.0/taichi_exec:.2f} shapes/sec)")
        print(f"  - Taichi JIT (Pure GPU pipeline)     : {taichi_pure_gpu_exec*1000:.2f} ms/shape ({1.0/taichi_pure_gpu_exec:.2f} shapes/sec)")
    else:
        print("  - Taichi JIT : N/A")
        
    if numba_eval and numba_eval.is_available():
        print(f"  - Numba JIT (CPU multithreaded)      : {numba_exec*1000:.2f} ms/shape ({1.0/numba_exec:.2f} shapes/sec)")
    else:
        print("  - Numba JIT (CPU multithreaded)      : N/A")
        

    engines = []
    if taichi_exec != 9999.0:
        engines.append(("Taichi Hybrid", taichi_exec))
    if taichi_pure_gpu_exec != 9999.0:
        engines.append(("Taichi Pure GPU", taichi_pure_gpu_exec))
    if numba_exec != 9999.0:
        engines.append(("Numba JIT", numba_exec))
        
    if len(engines) >= 2:
        engines.sort(key=lambda x: x[1])
        best_name, best_time = engines[0]
        second_name, second_time = engines[1]
        worst_name, worst_time = engines[-1]
        
        ratio_best_vs_worst = worst_time / best_time
        print(f"\n  >> Fastest: [{best_name}]")
        print(f"  >> {ratio_best_vs_worst:.2f}x faster than [{worst_name}]")
        
        if best_name == "Taichi 純 GPU 閉環" and second_name == "Taichi 混合":
            speedup_pure = second_time / best_time
            print(f"  >> Pure GPU pipeline is {speedup_pure:.2f}x faster than hybrid mode (PCIe overhead eliminated)")
            
    return taichi_exec, taichi_pure_gpu_exec, numba_exec

def run_benchmarks():
    print("======================================================================")
    print("              Taichi JIT vs. Numba JIT Benchmark")
    print("======================================================================")
    
    if not HAS_TAICHI:
        print("Error: Taichi not detected.")
        return
    if not HAS_NUMBA:
        print("Error: Numba not detected.")
        return
        
    benchmark_for_resolution(64, 64)
    benchmark_for_resolution(512, 512)

if __name__ == "__main__":
    run_benchmarks()
