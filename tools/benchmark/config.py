#!/usr/bin/env python3
"""Benchmark 常數與參考值定義。"""
import os

# ----------------------------------------------------------------------
# 端到端測試形狀數量
# ----------------------------------------------------------------------
TARGET_SHAPES_COUNT = 50

# ----------------------------------------------------------------------
# 預設測試時間參數
# ----------------------------------------------------------------------
DEFAULT_WARMUP_DURATION = 5.0
DEFAULT_TEST_DURATION = 60.0

# ----------------------------------------------------------------------
# 運算正確性歷史標準值 (Numba 50 Shapes 實際生成之 MSE)
# ----------------------------------------------------------------------
REFERENCE_MSE = {
    "Geometric": {
        "Tier_1": 274.0875,
        "Tier_2": 84.1177,
        "Tier_3": 84.1177
    },
    "Gradient": {
        "Tier_1": 146.7333,
        "Tier_2": 127.2739,
        "Tier_3": 127.2739
    },
    "High_Frequency": {
        "Tier_1": 3516.4910,
        "Tier_2": 3225.6494,
        "Tier_3": 3225.6494
    },
    "Alpha_Mask": {
        "Tier_1": 216.7076,
        "Tier_2": 87.5293,
        "Tier_3": 87.5293
    }
}

# ----------------------------------------------------------------------
# 標準參考機性能定義 (Ryzen 5600X + RTX 3060)
# ----------------------------------------------------------------------
BASELINE_REFERENCE = {
    "Tier_1": 2500.0,
    "Tier_2": 450.0,
    "Tier_3": 8.5
}


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
