#!/usr/bin/env python3
"""主跑分控制流程。"""

import argparse
import gc
import json
import os
import platform
import random
import sys
import time

import numpy as np

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

from benchmark.config import (
    BASELINE_REFERENCE,
    REFERENCE_MSE,
    TARGET_SHAPES_COUNT,
    load_profile_params,
)
from benchmark.engines import run_go_engine_benchmark, run_python_engine_benchmark
from benchmark.report import generate_html_report, generate_json_result
from benchmark.sysinfo import (
    get_cpu_model,
    get_git_info,
    get_gpu_driver_version,
    get_gpu_list,
    get_ram_size,
)
from benchmark.workloads import WORKLOADS
from evaluators import EvaluatorFactory

# ----------------------------------------------------------------------
# 鎖死全域隨機種子
# ----------------------------------------------------------------------
random.seed(42)
np.random.seed(42)


def run_benchmarks():
    parser = argparse.ArgumentParser(
        description="FH6 Painter Engine Performance Benchmarking Suite"
    )
    parser.add_argument(
        "--arch",
        type=str,
        default=None,
        choices=["Vulkan", "CUDA", "OpenGL", "CPU"],
        help="Force specific Taichi backend",
    )
    parser.add_argument(
        "--device", type=int, default=None, help="Force specific Taichi GPU Device ID"
    )
    parser.add_argument(
        "--no-history", action="store_true", help="Disable vertical historical saving"
    )
    parser.add_argument(
        "--clear-history",
        action="store_true",
        help="Clear historical JSON records before running",
    )
    parser.add_argument(
        "--duration", type=float, default=60.0, help="正式測試區間的秒數 (預設: 60.0)"
    )
    parser.add_argument(
        "--warmup-time", type=float, default=5.0, help="預熱時間秒數 (預設: 5.0)"
    )
    args = parser.parse_args()

    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    benchmark_dir = os.path.dirname(os.path.abspath(__file__))
    history_file = os.path.join(benchmark_dir, "benchmark_history.json")

    if args.clear_history:
        if os.path.exists(history_file):
            try:
                os.remove(history_file)
                print("[Setup] Historical benchmark records cleared.")
            except Exception as e:
                print(f"[Error] Failed to clear history: {e}")

    # Gather Environment Metadata
    git_info = get_git_info()
    cpu_model = get_cpu_model()
    gpu_models = get_gpu_list()
    gpu_model = gpu_models[0] if gpu_models else "Unknown GPU"
    gpu_driver = get_gpu_driver_version()
    ram_size = get_ram_size()

    # 鎖死 Taichi 全域隨機種子
    if HAS_TAICHI:
        try:
            arch_map = {
                "Vulkan": ti.vulkan,
                "CUDA": ti.cuda,
                "OpenGL": ti.opengl,
                "CPU": ti.cpu,
            }
            selected_arch = arch_map.get(args.arch) if args.arch else None
            if selected_arch:
                ti.init(arch=selected_arch, random_seed=42, log_level=ti.WARN)
                from evaluators.taichi_evaluator import TaichiEvaluator

                TaichiEvaluator._is_taichi_initialized = True
                TaichiEvaluator._taichi_arch_name = (
                    f"GPU - {args.arch}" if args.arch != "CPU" else "CPU"
                )
            else:
                backends = [
                    (ti.vulkan, "GPU - Vulkan"),
                    (ti.cuda, "GPU - CUDA"),
                    (ti.opengl, "GPU - OpenGL"),
                    (ti.cpu, "CPU"),
                ]
                for arch, name in backends:
                    try:
                        ti.init(arch=arch, random_seed=42, log_level=ti.WARN)
                        test = ti.field(dtype=ti.f32, shape=1)
                        test[0] = 1.0
                        from evaluators.taichi_evaluator import TaichiEvaluator

                        TaichiEvaluator._is_taichi_initialized = True
                        TaichiEvaluator._taichi_arch_name = name
                        break
                    except Exception:
                        continue
        except Exception as e:
            print(f"[Warning] Failed to lock Taichi seed: {e}")

    print("======================================================================")
    print("              FH6 PAINTER MARK - BENCHMARK SUITE")
    print("======================================================================")
    print(f"  [CPU]           : {cpu_model}")
    print(f"  [GPU]           : {gpu_model} (Driver: {gpu_driver})")
    print(f"  [RAM]           : {ram_size}")
    print(
        f"  [OS / PLATFORM] : {platform.system()} {platform.release()} ({platform.machine()})"
    )
    print(
        f"  [ENVIRONMENTS]  : Python {platform.python_version()} | Numba: {numba.__version__ if HAS_NUMBA else 'N/A'} | Taichi: {ti.__version__ if HAS_TAICHI else 'N/A'}"
    )
    print(f"  [GIT BRANCH]    : {git_info['branch']} (Commit: {git_info['commit']})")
    print("======================================================================")

    # 1. Parse Presets and Load Profiles
    settings_dir = os.path.join(project_root, "settings")
    fastest_ini = os.path.join(settings_dir, "a. keemstar fast - extremely fast.ini")
    balanced_ini = os.path.join(
        settings_dir, "c. balanced - good quality and speed.ini"
    )
    slowest_ini = os.path.join(
        settings_dir, "g. i hate my pc - yeahboiiiiis dad quality.ini"
    )

    presets = [
        {"name": "Tier_1", "profile_path": fastest_ini, "weight": 0.2},
        {"name": "Tier_2", "profile_path": balanced_ini, "weight": 0.6},
        {"name": "Tier_3", "profile_path": slowest_ini, "weight": 0.2},
    ]

    # 2. Dynamic Discovery of available Evaluators
    available_evals = EvaluatorFactory.get_available_evaluators()
    active_test_configs = []

    for e in available_evals:
        if not e["available"]:
            continue

        code = e["code"]
        if code == "TAICHI":
            for mode in [True, False]:
                mode_str = "Pure GPU Mode" if mode else "Hybrid Mode"
                active_test_configs.append(
                    {
                        "id": f"TAICHI_{'PURE' if mode else 'HYBRID'}",
                        "name": f"Taichi JIT ({mode_str})",
                        "class_code": "TAICHI",
                        "use_pure_gpu": mode,
                    }
                )
        else:
            active_test_configs.append(
                {
                    "id": code,
                    "name": e["name"],
                    "class_code": code,
                    "use_pure_gpu": False,
                }
            )

    if not active_test_configs:
        print("ERROR: No active acceleration engines are available.")
        sys.exit(1)

    print("\n[RUNNING TESTS]")
    print("> Generating Deterministic Test Images... [DONE]")

    # 準備標準測試圖 (512x512)
    w_t, h_t = 512, 512

    # 執行效能測試矩陣
    run_results = {}

    for config in active_test_configs:
        cfg_id = config["id"]
        cfg_name = config["name"]
        class_code = config["class_code"]
        use_pure_gpu = config["use_pure_gpu"]

        print(f"\n> Testing [{cfg_name}]")
        run_results[cfg_id] = {"name": cfg_name, "tiers": {}, "weighted_score": 0.0}

        for p in presets:
            tier_name = p["name"]
            profile_path = p["profile_path"]
            weight = p["weight"]

            batch_size, optimization_steps = load_profile_params(profile_path, 500, 80)

            workload_throughputs = []

            for wl in WORKLOADS:
                wl_name = wl["name"]
                target_img, alpha_mask = wl["generator"](w_t, h_t)

                # 建立評估器
                if class_code == "TAICHI":
                    evaluator = EvaluatorFactory.create_evaluator(
                        "TAICHI",
                        target_img,
                        alpha_mask,
                        taichi_arch=args.arch,
                        taichi_device_id=args.device,
                    )
                else:
                    evaluator = EvaluatorFactory.create_evaluator(
                        class_code, target_img, alpha_mask
                    )

                # 預熱 (JIT compile)
                try:
                    if class_code == "GO_OPENCL":
                        run_go_engine_benchmark(
                            evaluator,
                            target_img,
                            alpha_mask,
                            profile_path,
                            project_root,
                            warmup=True,
                        )
                    else:
                        params_warm = {
                            "optimization_steps": 1,
                            "check_contour": alpha_mask is not None,
                            "use_importance": False,
                            "error_prob": np.ones((h_t, w_t), dtype=np.float32),
                            "use_freeze": False,
                            "use_weight": False,
                            "use_uncovered": True,
                            "use_pure_gpu": use_pure_gpu,
                        }
                        run_python_engine_benchmark(
                            evaluator,
                            target_img,
                            alpha_mask,
                            batch_size,
                            params_warm,
                            warmup=True,
                        )
                except Exception as ex:
                    print(f"  [Warm-up Warning] {cfg_name} on {wl_name} failed: {ex}")

                # 正式計時測試
                t_shapes, t_sec, final_mse = 0, 1.0, 999999.0
                try:
                    if class_code == "GO_OPENCL":
                        t_shapes, t_sec, final_mse = run_go_engine_benchmark(
                            evaluator,
                            target_img,
                            alpha_mask,
                            profile_path,
                            project_root,
                            warmup=False,
                            duration=args.duration,
                        )
                    else:
                        params_run = {
                            "optimization_steps": optimization_steps,
                            "check_contour": alpha_mask is not None,
                            "use_importance": False,
                            "error_prob": np.ones((h_t, w_t), dtype=np.float32),
                            "use_freeze": False,
                            "use_weight": False,
                            "use_uncovered": True,
                            "use_pure_gpu": use_pure_gpu,
                        }
                        t_shapes, t_sec, final_mse = run_python_engine_benchmark(
                            evaluator,
                            target_img,
                            alpha_mask,
                            batch_size,
                            params_run,
                            warmup=False,
                            duration=args.duration,
                        )
                except Exception as ex:
                    print(f"  [Execution Error] {cfg_name} on {wl_name} failed: {ex}")

                evaluator.cleanup()
                del evaluator
                gc.collect()

                # 計算 Throughput
                wl_throughput = t_shapes / t_sec if t_sec > 0 else 0.0

                # 運算正確性驗證 (防作弊)
                is_valid = True
                ref_limit = (
                    REFERENCE_MSE.get(wl_name, {}).get(tier_name, 999999.0) * 1.05
                )

                if t_shapes >= TARGET_SHAPES_COUNT and final_mse > ref_limit:
                    is_valid = False
                    wl_throughput = 0.0

                workload_throughputs.append(wl_throughput)

            # 計算該 Tier 的平均 Throughput 與得分
            avg_throughput = (
                np.mean(workload_throughputs) if workload_throughputs else 0.0
            )
            baseline = BASELINE_REFERENCE.get(tier_name, 1.0)
            if is_valid:
                score = (avg_throughput / baseline) * 1000.0
            else:
                score = 0
            run_results[cfg_id]["tiers"][tier_name] = {
                "throughput": avg_throughput,
                "score": score,
            }

            run_results[cfg_id]["weighted_score"] += score * weight

            print(
                f"  - {tier_name:18} : {avg_throughput:7.1f} shapes/sec  ... [Score: {int(score)}]"
            )

        print(
            f"  > Engine Weighted Score: {int(run_results[cfg_id]['weighted_score'])} pts"
        )

    # 5. 排行榜
    print("\n======================================================================")
    print("                     *** FINAL BENCHMARK LEADERBOARD")
    print("======================================================================")

    leaderboard = []
    for cfg_id, info in run_results.items():
        leaderboard.append(
            {
                "id": cfg_id,
                "name": info["name"],
                "weighted_score": info["weighted_score"],
                "tiers": info["tiers"],
            }
        )

    leaderboard.sort(key=lambda x: x["weighted_score"], reverse=True)

    for rank, entry in enumerate(leaderboard, 1):
        score_int = int(entry["weighted_score"])
        badge = f"#{rank}"
        print(f"  {badge:5} | {entry['name']:40} | {score_int:6} pts")
    print("======================================================================")

    # 歷史版本對比與衰退檢查
    history_records = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_records = json.load(f)
        except Exception:
            pass

    previous_baseline = None
    for record in reversed(history_records):
        if record.get("cpu") == cpu_model and record.get("gpu") == gpu_model:
            previous_baseline = record
            break

    if not previous_baseline and history_records:
        previous_baseline = history_records[-1]

    has_regression = False
    if previous_baseline:
        print(
            "\n======================================================================"
        )
        print("                  *** VERTICAL VERSION COMPATIBILITY COMPARISON")
        print("======================================================================")
        base_commit = previous_baseline.get("git_commit", "N/A")
        base_time = previous_baseline.get("timestamp", "N/A")
        print("  Comparing against baseline version:")
        print(f"  - Target Commit: {base_commit} | Timestamp: {base_time}")
        print("  --------------------------------------------------------------------")

        base_engines = previous_baseline.get("engines", {})
        for entry in leaderboard:
            cfg_id = entry["id"]
            if cfg_id in base_engines:
                base_score = base_engines[cfg_id]["weighted_score"]
                curr_score = entry["weighted_score"]
                diff_pct = (
                    ((curr_score - base_score) / base_score) * 100.0
                    if base_score > 0
                    else 0.0
                )

                if diff_pct < -10.0:
                    has_regression = True
                    alert = "[REGRESSION WARNING] (>10% slower!)"
                elif diff_pct > 5.0:
                    alert = "[PERFORMANCE IMPROVED]"
                else:
                    alert = "[STABLE]"

                sign = "+" if diff_pct >= 0 else ""
                print(
                    f"  - {entry['name']:35} : {int(curr_score):5} pts vs baseline {int(base_score):5} pts ({sign}{diff_pct:+.1f}%) {alert}"
                )
            else:
                print(
                    f"  - {entry['name']:35} : {int(entry['weighted_score']):5} pts vs baseline (N/A, new method added)"
                )
        print("======================================================================")

    # 寫入當前紀錄到歷史資料庫 (上限 50 筆)
    if not args.no_history:
        current_record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "git_commit": git_info["commit"],
            "git_branch": git_info["branch"],
            "git_message": git_info["message"],
            "cpu": cpu_model,
            "gpu": gpu_model,
            "gpu_driver": gpu_driver,
            "ram": ram_size,
            "python_version": platform.python_version(),
            "engines": {
                entry["id"]: {
                    "name": entry["name"],
                    "weighted_score": entry["weighted_score"],
                    "tiers": entry["tiers"],
                }
                for entry in leaderboard
            },
        }
        history_records.append(current_record)
        if len(history_records) > 50:
            history_records.pop(0)

        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history_records, f, indent=2)
            print(
                "\n[Storage] Current benchmark metrics successfully archived in history database."
            )
        except Exception as e:
            print(f"\n[Warning] Failed to archive benchmark metrics: {e}")

    # 輸出報表
    system_info = {
        "cpu": cpu_model,
        "gpu": gpu_model,
        "gpu_driver": gpu_driver,
        "ram": ram_size,
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
    }

    result_json_path = os.path.join(benchmark_dir, "benchmark_result.json")
    generate_json_result(result_json_path, leaderboard, system_info)

    report_html_path = os.path.join(benchmark_dir, "benchmark_report.html")
    generate_html_report(report_html_path, leaderboard, system_info)

    if has_regression:
        print(
            "\n[CI Alert] System execution performance regression detected. Verify latest commits."
        )
        sys.exit(1)
    else:
        sys.exit(0)
