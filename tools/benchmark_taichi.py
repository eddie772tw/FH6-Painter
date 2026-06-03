#!/usr/bin/env python3
import sys
import os
import time
import json
import platform
import argparse
import numpy as np

# Adjust path to import from parent directory
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

from evaluators import EvaluatorFactory

def get_cpu_model():
    """Reads precise CPU brand name on Windows/Linux/macOS."""
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            return cpu_name.strip()
        except Exception:
            pass
    return platform.processor() or "Unknown CPU"

def get_gpu_list():
    """Reads GPU model description using native winreg on Windows."""
    gpus = []
    if platform.system() == "Windows":
        try:
            import winreg
            path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        if subkey_name.isdigit():
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                gpu_name, _ = winreg.QueryValueEx(subkey, "DriverDesc")
                                if gpu_name and gpu_name not in gpus:
                                    gpus.append(gpu_name)
                    except Exception:
                        pass
        except Exception:
            pass
    return gpus if gpus else ["Unknown GPU Device"]

def get_git_info():
    """Gathers current Git branch, commit hash, and last message summary."""
    try:
        import subprocess
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        msg = subprocess.check_output(["git", "log", "-1", "--pretty=%s"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        return {"commit": commit, "branch": branch, "message": msg}
    except Exception:
        return {"commit": "N/A", "branch": "N/A", "message": "N/A"}

def load_profile_params(profile_path, default_batch, default_steps):
    """Loads randomSamples (batch_size) and mutatedSamples (optimization_steps) from .ini file."""
    batch_size = default_batch
    steps = default_steps
    if profile_path and os.path.exists(profile_path):
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith(";"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip()
                        if key == "randomSamples":
                            batch_size = int(val)
                        elif key == "mutatedSamples":
                            steps = int(val)
        except Exception as e:
            print(f"[Warning] Failed to parse profile {os.path.basename(profile_path)}: {e}")
    return batch_size, steps

def run_preset_benchmark(evaluator, res_w, res_h, batch_size, optimization_steps, use_pure_gpu, run_count=5):
    """Runs a benchmark for a single setup and measures precise execution timing."""
    target_img = np.random.rand(res_h, res_w, 3).astype(np.float32) * 255.0
    current_canvas = np.zeros_like(target_img)
    
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
        "optimization_steps": optimization_steps,
        "use_pure_gpu": use_pure_gpu
    }
    
    # Warm-up (1 run) to compile JIT kernels
    try:
        evaluator.search_best_shape(current_canvas, batch_size, params)
        if HAS_TAICHI:
            ti.sync()
    except Exception as e:
        print(f"  [Warm-up error] {e}")
        return 9999.0

    # Precise timing loops
    t_start = time.perf_counter()
    for _ in range(run_count):
        try:
            evaluator.search_best_shape(current_canvas, batch_size, params)
        except Exception as e:
            print(f"  [Execution error] {e}")
            return 9999.0
    if HAS_TAICHI:
        ti.sync()
    elapsed = time.perf_counter() - t_start
    return elapsed / run_count

def run_benchmarks():
    parser = argparse.ArgumentParser(description="FH6 Painter Engine Performance Benchmarking Suite")
    parser.add_argument("--arch", type=str, default=None, choices=["Vulkan", "CUDA", "OpenGL", "CPU"], help="Force specific Taichi backend")
    parser.add_argument("--device", type=int, default=None, help="Force specific Taichi GPU Device ID")
    parser.add_argument("--no-history", action="store_true", help="Disable vertical historical saving")
    parser.add_argument("--clear-history", action="store_true", help="Clear historical JSON records before running")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_history.json")

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
    
    print("======================================================================")
    print("        FH6 PAINTER STUDIO - HIGH PERFORMANCE BENCHMARK SUITE")
    print("======================================================================")
    print(f"  [OS / PLATFORM] : {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"  [PROCESSOR]     : {cpu_model}")
    print(f"  [GRAPHICS]      : {gpu_model}")
    print(f"  [ENVIRONMENTS]  : Python {platform.python_version()} | Numba: {numba.__version__ if HAS_NUMBA else 'N/A'} | Taichi: {ti.__version__ if HAS_TAICHI else 'N/A'}")
    print(f"  [GIT BRANCH]    : {git_info['branch']} (Commit: {git_info['commit']})")
    print(f"  [COMMIT MSG]    : {git_info['message']}")
    print("======================================================================")

    # 1. Parse Presets and cap Slowest profile for reasonable test duration
    settings_dir = os.path.join(project_root, "settings")
    
    fastest_ini = os.path.join(settings_dir, "a. keemstar fast - extremely fast.ini")
    balanced_ini = os.path.join(settings_dir, "c. balanced - good quality and speed.ini")
    slowest_ini = os.path.join(settings_dir, "g. i hate my pc - yeahboiiiiis dad quality.ini")

    fast_b, fast_s = load_profile_params(fastest_ini, 500, 80)
    bal_b, bal_s = load_profile_params(balanced_ini, 5000, 500)
    slow_b, slow_s = load_profile_params(slowest_ini, 1000000, 2000)

    # Capping slowest preset to prevent massive system freeze on CPU modes
    slow_b_capped = min(slow_b, 20000)
    slow_s_capped = min(slow_s, 1000)

    presets = [
        {"name": "Fastest (極速)", "batch": fast_b, "steps": fast_s, "weight": 0.2, "runs": 10},
        {"name": "Balanced (平衡)", "batch": bal_b, "steps": bal_s, "weight": 0.5, "runs": 5},
        {"name": "Slowest (高品質-等比限縮)", "batch": slow_b_capped, "steps": slow_s_capped, "weight": 0.3, "runs": 3}
    ]

    print("\n[Presets Configured for Benchmark]")
    for p in presets:
        print(f"  - {p['name']}: {p['batch']} samples | {p['steps']} steps | Weight: {int(p['weight']*100)}% | Runs: {p['runs']}")
    print("======================================================================")

    # 2. Dynamic Discovery of available Evaluators
    available_evals = EvaluatorFactory.get_available_evaluators()
    
    # 3. Execution Benchmarks across Resolutions
    resolutions = [(64, 64), (512, 512)]
    run_results = {}

    for res_w, res_h in resolutions:
        print(f"\n--> Run Stress-Test Resolution: {res_w} x {res_h}...")
        
        # Instantiate evaluators fresh for each resolution to avoid pre-allocated shape mismatches
        active_test_configs = []
        mock_target = np.zeros((res_h, res_w, 3), dtype=np.float32)

        for e in available_evals:
            if not e["available"]:
                continue
            
            code = e["code"]
            if code == "TAICHI":
                try:
                    eval_inst = EvaluatorFactory.create_evaluator(
                        "TAICHI",
                        mock_target,
                        taichi_arch=args.arch,
                        taichi_device_id=args.device
                    )
                    if eval_inst.is_available():
                        # For Taichi, we benchmark both Hybrid Mode and Pure GPU Mode sharing the same instance
                        for mode in [True, False]:
                            mode_str = "Pure GPU Mode" if mode else "Hybrid Mode"
                            active_test_configs.append({
                                "id": f"TAICHI_{'PURE' if mode else 'HYBRID'}",
                                "name": f"Taichi JIT ({eval_inst.get_name().split('(')[-1].rstrip(')')}, {mode_str})",
                                "class_code": "TAICHI",
                                "use_pure_gpu": mode,
                                "evaluator": eval_inst
                            })
                except Exception as ex:
                    print(f"[Warning] Failed to instantiate Taichi JIT: {ex}")
            else:
                try:
                    eval_inst = EvaluatorFactory.create_evaluator(code, mock_target)
                    if eval_inst.is_available():
                        active_test_configs.append({
                            "id": code,
                            "name": eval_inst.get_name(),
                            "class_code": code,
                            "use_pure_gpu": False,
                            "evaluator": eval_inst
                        })
                except Exception as ex:
                    print(f"[Warning] Failed to instantiate {e['name']}: {ex}")

        if not active_test_configs:
            print("ERROR: No active acceleration engines are available for this resolution.")
            continue

        for config in active_test_configs:
            cfg_id = config["id"]
            cfg_name = config["name"]
            evaluator = config["evaluator"]
            use_pure_gpu = config["use_pure_gpu"]

            if cfg_id not in run_results:
                run_results[cfg_id] = {
                    "name": cfg_name,
                    "presets": {},
                    "weighted_time": 0.0,
                    "weighted_speed": 0.0
                }

            print(f"  Testing engine: {cfg_name}...")
            
            weighted_time = 0.0
            preset_times = {}

            for p in presets:
                p_name = p["name"]
                t_avg = run_preset_benchmark(
                    evaluator, res_w, res_h, 
                    p["batch"], p["steps"], 
                    use_pure_gpu, p["runs"]
                )
                preset_times[p_name] = t_avg
                weighted_time += t_avg * p["weight"]
                if t_avg < 9000.0:
                    print(f"    - Preset: {p_name} : {t_avg*1000:.2f} ms/shape")
                else:
                    print(f"    - Preset: {p_name} : Failed/Skipped")

            weighted_speed = 1.0 / weighted_time if weighted_time > 0 and weighted_time < 9000.0 else 0.0
            
            run_results[cfg_id]["presets"][f"{res_w}x{res_h}"] = preset_times
            # Accumulate weighted results across resolutions (average weighted speed)
            run_results[cfg_id]["weighted_time"] += weighted_time / len(resolutions)
            run_results[cfg_id]["weighted_speed"] += weighted_speed / len(resolutions)

        # 4. Clean up Evaluator resources for this resolution
        # Clean up each unique evaluator instance exactly once
        cleaned_evaluators = set()
        for config in active_test_configs:
            eval_inst = config["evaluator"]
            if eval_inst not in cleaned_evaluators:
                try:
                    eval_inst.cleanup()
                except Exception:
                    pass
                cleaned_evaluators.add(eval_inst)

    # 5. Horizontal Comparison and Leaderboard Output
    print("\n======================================================================")
    print("                     *** FINAL BENCHMARK LEADERBOARD")
    print("======================================================================")
    
    leaderboard = []
    for cfg_id, info in run_results.items():
        leaderboard.append({
            "id": cfg_id,
            "name": info["name"],
            "weighted_time": info["weighted_time"],
            "weighted_speed": info["weighted_speed"]
        })
    
    # Sort by fastest execution time
    leaderboard.sort(key=lambda x: x["weighted_time"])

    for rank, entry in enumerate(leaderboard, 1):
        perf_indicator = f"{entry['weighted_time']*1000:.2f} ms/shape" if entry["weighted_time"] < 9000.0 else "N/A (Failed)"
        throughput = f"{entry['weighted_speed']:.2f} shapes/sec" if entry["weighted_speed"] > 0 else "N/A"
        badge = "FASTEST" if rank == 1 else f"#{rank}"
        print(f"  {badge:10} | {entry['name']:40} | {perf_indicator:15} | {throughput}")

    if len(leaderboard) >= 2 and leaderboard[0]["weighted_time"] < 9000.0:
        fastest = leaderboard[0]
        slowest = leaderboard[-1]
        if slowest["weighted_time"] < 9000.0:
            ratio = slowest["weighted_time"] / fastest["weighted_time"]
            print(f"\n  >> [{fastest['name']}] is {ratio:.2f}x faster than [{slowest['name']}] (Weighted Profile)")

    # 6. Vertical Historical Comparisons & Regression Checking
    history_records = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_records = json.load(f)
        except Exception as e:
            print(f"\n[Warning] Failed to load performance history file: {e}")

    # Find the latest baseline record with the same CPU and GPU configuration
    previous_baseline = None
    for record in reversed(history_records):
        if record.get("cpu") == cpu_model and record.get("gpu") == gpu_model:
            previous_baseline = record
            break

    # If no matching hardware baseline exists, fallback to the absolute latest record
    if not previous_baseline and history_records:
        previous_baseline = history_records[-1]

    has_regression = False
    if previous_baseline:
        print("\n======================================================================")
        print("                  *** VERTICAL VERSION COMPATIBILITY COMPARISON")
        print("======================================================================")
        base_commit = previous_baseline.get("git_commit", "N/A")
        base_time = previous_baseline.get("timestamp", "N/A")
        print(f"  Comparing against baseline version:")
        print(f"  - Target Commit: {base_commit} | Timestamp: {base_time}")
        if previous_baseline.get("cpu") == cpu_model and previous_baseline.get("gpu") == gpu_model:
            print(f"  - Hardware Setup: MATCHED (Same CPU and GPU)")
        else:
            print(f"  - Hardware Setup: MISMATCHED (Comparing across platforms: baseline CPU={previous_baseline.get('cpu')})")
        print("  --------------------------------------------------------------------")

        base_engines = previous_baseline.get("engines", {})
        for entry in leaderboard:
            cfg_id = entry["id"]
            if cfg_id in base_engines:
                base_time_ms = base_engines[cfg_id]["weighted_time"] * 1000.0
                curr_time_ms = entry["weighted_time"] * 1000.0
                diff_pct = ((curr_time_ms - base_time_ms) / base_time_ms) * 100.0

                if diff_pct > 10.0:
                    has_regression = True
                    alert = "[REGRESSION WARNING] (>10% slower!)"
                    color_prefix = "\033[91m"
                    color_suffix = "\033[0m"
                elif diff_pct < -5.0:
                    alert = "[PERFORMANCE IMPROVED]"
                    color_prefix = "\033[92m"
                    color_suffix = "\033[0m"
                else:
                    alert = "[STABLE]"
                    color_prefix = ""
                    color_suffix = ""

                sign = "+" if diff_pct >= 0 else ""
                print(f"  {color_prefix}- {entry['name']:35} : {curr_time_ms:7.2f} ms vs baseline {base_time_ms:7.2f} ms ({sign}{diff_pct:+.1f}%) {alert}{color_suffix}")
            else:
                print(f"  - {entry['name']:35} : {entry['weighted_time']*1000.0:7.2f} ms vs baseline (N/A, new method added)")
        print("======================================================================")

    # 7. Write current record to history (Limit to 50 records)
    if not args.no_history:
        current_record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "git_commit": git_info["commit"],
            "git_branch": git_info["branch"],
            "git_message": git_info["message"],
            "cpu": cpu_model,
            "gpu": gpu_model,
            "python_version": platform.python_version(),
            "engines": {
                entry["id"]: {
                    "name": entry["name"],
                    "weighted_time": entry["weighted_time"],
                    "weighted_speed": entry["weighted_speed"]
                } for entry in leaderboard
            }
        }
        history_records.append(current_record)
        if len(history_records) > 50:
            history_records.pop(0)

        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history_records, f, indent=2)
            print(f"\n[Storage] Current benchmark metrics successfully archived in history database.")
        except Exception as e:
            print(f"\n[Warning] Failed to archive benchmark metrics: {e}")

    # Set non-zero exit status if performance regressed to warn downstream CI tasks
    if has_regression:
        print("\n[CI Alert] System execution performance regression detected. Verify latest commits.")
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    run_benchmarks()
