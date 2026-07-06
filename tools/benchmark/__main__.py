#!/usr/bin/env python3
"""FH6 Painter Mark - Benchmark Suite CLI 入口點。

用法：
    python tools/benchmark/__main__.py [OPTIONS]
    python -m benchmark [OPTIONS]  (從 tools/ 資料夾執行)
"""

import os
import sys

# 確保專案根目錄在 sys.path 中
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
# 確保 tools/ 目錄在 sys.path 中 (以便 import benchmark 套件)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.runner import run_benchmarks

if __name__ == "__main__":
    run_benchmarks()
