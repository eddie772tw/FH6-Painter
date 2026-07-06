import os
import sys
import time

import numpy as np

# 將專案根目錄加入 path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evaluators.taichi_evaluator import TaichiEvaluator


def run_pso_benchmark():
    print("=== TaichiJIT GPU PSO Optimization Benchmark ===")

    # 建立一個 Target 影像：單色背景中放一個紅色的圓
    height, width = 256, 256
    target = np.zeros((height, width, 3), dtype=np.float32)
    # 畫一個紅色的橢圓
    Y, X = np.ogrid[:height, :width]
    mask = ((X - 128) ** 2) / (60**2) + ((Y - 128) ** 2) / (40**2) <= 1.0
    target[mask] = [1.0, 0.0, 0.0]

    # 初始化 Canvas 為黑底
    canvas = np.zeros((height, width, 3), dtype=np.float32)

    # 初始化 Evaluator
    evaluator = TaichiEvaluator(target, taichi_arch="Vulkan")
    if not evaluator.is_available():
        print("Vulkan 不可用，嘗試 CUDA...")
        evaluator = TaichiEvaluator(target, taichi_arch="CUDA")
        if not evaluator.is_available():
            print("CUDA 不可用，嘗試 CPU...")
            evaluator = TaichiEvaluator(target, taichi_arch="CPU")

    if not evaluator.is_available():
        print("錯誤：Taichi JIT Evaluator 無法初始化或不可用！")
        return

    params = {
        "use_pure_gpu": True,
        "optimization_steps": 50,
        "current_max_r": 80.0,
        "use_importance": False,
        "sa_enabled": False,
    }

    # 1. 驗證粒子群坍縮 (Particle Collapse Verification)
    print("\n1. 驗證粒子群坍縮 (Particle Collapse Verification)...")
    test_canvas = canvas.copy()
    evaluator.canvas_initialized = False
    best_shape, delta = evaluator.search_best_shape(
        test_canvas, batch_size=2048, params=params
    )

    # 讀取 GPU 上的 pbest 狀態
    pbest_x = evaluator.ti_pbest_x.to_numpy()
    pbest_fit = evaluator.ti_pbest_fit.to_numpy()

    # 計算 128 個粒子幾何參數的標準差
    std_geom = np.std(pbest_x[:, :5], axis=0)
    std_fit = np.std(pbest_fit)

    print("  128 個粒子結束時的參數標準差:")
    print(f"    x_c std: {std_geom[0]:.6f}")
    print(f"    y_c std: {std_geom[1]:.6f}")
    print(f"    r_x std: {std_geom[2]:.6f}")
    print(f"    r_y std: {std_geom[3]:.6f}")
    print(f"    theta std: {std_geom[4]:.6f}")
    print(f"    適應度 std: {std_fit:.6f}")

    if np.all(std_geom < 1e-1) and std_fit < 1e-1:
        print("  [成功] 128 個粒子已成功坍縮至同一個最佳候選 (std 接近 0)！")
    else:
        print("  [注意] 粒子未完全坍縮，可能需要增加坍縮步數或調整學習因子。")

    # 2. 驗證固定起點下的 PSO 決定性 (Deterministic PSO with Fixed Start)
    print("\n2. 驗證固定起點下的 PSO 決定性 (Deterministic PSO with Fixed Start)...")
    fixed_results = []

    # 模擬 10 次基於相同初始最佳解的優化 (前 5 次為 JIT 熱身)
    for run in range(10):
        # 重設 canvas
        evaluator.canvas_initialized = False
        evaluator.ti_canvas.from_numpy(canvas.astype(np.float32))

        # 動態分拆 canvas
        from evaluators.taichi_evaluator import (
            finalize_pso_result_gpu,
            split_canvas_to_planar_gpu,
            taichi_pso_epoch_gpu,
        )

        split_canvas_to_planar_gpu(
            evaluator.ti_canvas,
            evaluator.ti_canvas_r,
            evaluator.ti_canvas_g,
            evaluator.ti_canvas_b,
            height,
            width,
        )

        # 設定固定起點的 best_candidate
        init_best = np.zeros((1, 10), dtype=np.float32)
        init_best[0, 0:6] = [120.0, 120.0, 50.0, 35.0, 0.5, 255.0]
        init_best[0, 9] = 9999999.0
        evaluator.ti_best_candidate.from_numpy(init_best)

        # 決定性初始化
        rng = np.random.default_rng(seed=42)
        particles_x_np = np.zeros((128, 6), dtype=np.float32)
        particles_x_np[0] = init_best[0, 0:6]
        for k in range(1, 128):
            particles_x_np[k, 0] = np.clip(
                init_best[0, 0] + rng.normal(0, 8.0), 0.0, width
            )
            particles_x_np[k, 1] = np.clip(
                init_best[0, 1] + rng.normal(0, 8.0), 0.0, height
            )
            particles_x_np[k, 2] = np.clip(
                init_best[0, 2] + rng.normal(0, 6.0), 2.0, 80.0
            )
            particles_x_np[k, 3] = np.clip(
                init_best[0, 3] + rng.normal(0, 6.0), 2.0, 80.0
            )
            particles_x_np[k, 4] = init_best[0, 4] + rng.normal(0, 0.25)
            particles_x_np[k, 5] = 255.0

        evaluator.ti_particles_x.from_numpy(particles_x_np)
        evaluator.ti_pbest_x.from_numpy(particles_x_np)

        particles_v_np = np.zeros((128, 5), dtype=np.float32)
        evaluator.ti_particles_v.from_numpy(particles_v_np)

        pbest_fit_np = np.full((128,), 999999999.0, dtype=np.float32)
        pbest_fit_np[0] = 9999999.0
        evaluator.ti_pbest_fit.from_numpy(pbest_fit_np)

        # seeds 決定性重置
        seeds_np = (np.arange(128, dtype=np.uint32) * 1664525 + 1013904223).astype(
            np.uint32
        )
        evaluator.ti_seeds.from_numpy(seeds_np)

        # 執行 50 步 PSO
        total_steps = 50
        steps_per_epoch = 5
        num_epochs = total_steps // steps_per_epoch
        check_contour_jit = 0
        use_freeze = 0

        for epoch in range(num_epochs):
            step_offset = epoch * steps_per_epoch
            from evaluators.taichi_evaluator import copy_pbest_gpu

            copy_pbest_gpu(
                evaluator.ti_pbest_x,
                evaluator.ti_pbest_x_old,
                evaluator.ti_pbest_fit,
                evaluator.ti_pbest_fit_old,
            )
            taichi_pso_epoch_gpu(
                evaluator.ti_particles_x,
                evaluator.ti_particles_v,
                evaluator.ti_pbest_x,
                evaluator.ti_pbest_fit,
                evaluator.ti_pbest_x_old,
                evaluator.ti_pbest_fit_old,
                evaluator.ti_seeds,
                evaluator.ti_target_r,
                evaluator.ti_target_g,
                evaluator.ti_target_b,
                evaluator.ti_canvas_r,
                evaluator.ti_canvas_g,
                evaluator.ti_canvas_b,
                evaluator.ti_alpha,
                check_contour_jit,
                use_freeze,
                evaluator.ti_empty_u8,
                0,
                evaluator.ti_empty_f32,
                0,
                evaluator.ti_empty_f32,
                height,
                width,
                80.0,
                step_offset,
                total_steps,
            )

            pbest_fit_np = evaluator.ti_pbest_fit.to_numpy()
            best_idx = np.argmin(pbest_fit_np)
            if best_idx != 0:
                pbest_x_np = evaluator.ti_pbest_x.to_numpy()
                pbest_x_np[[0, best_idx]] = pbest_x_np[[best_idx, 0]]
                pbest_fit_np[[0, best_idx]] = pbest_fit_np[[best_idx, 0]]
                evaluator.ti_pbest_x.from_numpy(pbest_x_np)
                evaluator.ti_pbest_fit.from_numpy(pbest_fit_np)

        # finalize
        finalize_pso_result_gpu(
            evaluator.ti_pbest_x,
            evaluator.ti_pbest_fit,
            evaluator.ti_best_candidate,
            evaluator.ti_target_r,
            evaluator.ti_target_g,
            evaluator.ti_target_b,
            evaluator.ti_canvas_r,
            evaluator.ti_canvas_g,
            evaluator.ti_canvas_b,
            evaluator.ti_alpha,
            check_contour_jit,
            use_freeze,
            evaluator.ti_empty_u8,
            0,
            evaluator.ti_empty_f32,
            0,
            evaluator.ti_empty_f32,
            height,
            width,
        )

        final_best = evaluator.ti_best_candidate.to_numpy()
        if run < 5:
            print(
                f"  (熱身) 第 {run + 1} 次執行: 最佳形狀 {final_best[0, 0:5]}, MSE = {final_best[0, 9]:.4f}"
            )
        else:
            fixed_results.append((final_best[0, 0:5].copy(), final_best[0, 9]))
            print(
                f"  第 {run - 4} 次執行: 最佳形狀 {final_best[0, 0:5]}, MSE = {final_best[0, 9]:.4f}"
            )

    # 決定性比對
    first_shape, first_delta = fixed_results[0]
    fixed_all_match = True
    for shape, delta in fixed_results[1:]:
        if not np.allclose(shape, first_shape, atol=1e-5) or not np.isclose(
            delta, first_delta, atol=1e-5
        ):
            fixed_all_match = False
            break

    if fixed_all_match:
        print("  [成功] 固定起點下，五次獨立優化的輸出完全一致，PSO 核心 100% 決定性！")
    else:
        print("  [失敗] 輸出不一致，PSO 核心非決定性！")

    # 3. 測試效能與收斂性
    print("\n3. 評估擬合效果與效能...")
    t0 = time.perf_counter()
    best_shape, delta = evaluator.search_best_shape(
        canvas, batch_size=4096, params=params
    )
    t1 = time.perf_counter()

    print(f"  總執行時間: {(t1 - t0) * 1000:.2f} ms")
    print("  最佳擬合參數:")
    print(f"    中心: ({best_shape[0]:.2f}, {best_shape[1]:.2f})")
    print(f"    半徑: ({best_shape[2]:.2f}, {best_shape[3]:.2f})")
    print(f"    旋轉角: {best_shape[4]:.4f} 弧度")
    print(
        f"    顏色 (RGB): ({best_shape[5]:.2f}, {best_shape[6]:.2f}, {best_shape[7]:.2f})"
    )
    print(f"    Alpha: {best_shape[8]:.2f}")
    print(f"    適應度 (Delta MSE): {delta:.4f}")

    evaluator.cleanup()


if __name__ == "__main__":
    run_pso_benchmark()
