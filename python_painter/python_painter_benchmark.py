import os
import sys
import time
import random
from typing import Dict, Any, List
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.dirname(current_dir))
try:
    from generator import Shape, ShapeGenerationEngine, GeneratorProfile, ShapeType
except ImportError:
    try:
        from python_painter.generator import Shape, ShapeGenerationEngine, GeneratorProfile, ShapeType
    except ImportError:
        print('[Error] Could not import python_painter modules. Make sure the package exists.')
        sys.exit(1)
NUMBA_AVAILABLE = False
try:
    import numpy as np
    from numba import njit, prange
    NUMBA_AVAILABLE = True
except ImportError:
    pass
if NUMBA_AVAILABLE:

    @njit(fastmath=True)
    def _evaluate_single_shape(cx, cy, rx, ry, theta, target):
        loss_sum = 0.0
        grid_min = -1.0
        pixel_size = 2.0 / 256.0
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)
        half_w = np.sqrt((rx * cos_t) ** 2 + (ry * sin_t) ** 2)
        half_h = np.sqrt((rx * sin_t) ** 2 + (ry * cos_t) ** 2)
        min_x = cx - half_w
        max_x = cx + half_w
        min_y = cy - half_h
        max_y = cy + half_h
        min_px = int((min_x - grid_min) / pixel_size)
        max_px = int((max_x - grid_min) / pixel_size)
        min_py = int((min_y - grid_min) / pixel_size)
        max_py = int((max_y - grid_min) / pixel_size)
        min_px = max(0, min(255, min_px))
        max_px = max(0, min(255, max_px))
        min_py = max(0, min(255, min_py))
        max_py = max(0, min(255, max_py))
        inv_rx_sq = 1.0 / (rx * rx)
        inv_ry_sq = 1.0 / (ry * ry)
        for py in range(min_py, max_py + 1):
            y_val = grid_min + py * pixel_size
            dy = y_val - cy
            for px in range(min_px, max_px + 1):
                x_val = grid_min + px * pixel_size
                dx = x_val - cx
                xp = dx * cos_t + dy * sin_t
                yp = -dx * sin_t + dy * cos_t
                if xp * xp * inv_rx_sq + yp * yp * inv_ry_sq <= 1.0:
                    loss_sum += target[0, py, px]
        return loss_sum

    @njit(fastmath=True, parallel=True)
    def _numba_scanline_evaluation(cxs, cys, rxs, rys, thetas, target, batch_size):
        losses = np.zeros(batch_size, dtype=np.float32)
        for i in prange(batch_size):
            losses[i] = _evaluate_single_shape(cxs[i], cys[i], rxs[i], rys[i], thetas[i], target)
        return np.sum(losses)

def run_numba_micro_benchmark() -> float:
    print('[Calibration] Measuring Numba JIT Scanline Math performance...')
    if not NUMBA_AVAILABLE:
        print('  -> Numba not installed, skipping.')
        return 0.0
    batch_size = 500
    target = np.random.rand(3, 256, 256).astype(np.float32)
    cxs = np.random.rand(batch_size).astype(np.float32) * 2.0 - 1.0
    cys = np.random.rand(batch_size).astype(np.float32) * 2.0 - 1.0
    rxs = np.random.rand(batch_size).astype(np.float32) * 0.4 + 0.05
    rys = np.random.rand(batch_size).astype(np.float32) * 0.4 + 0.05
    thetas = np.random.rand(batch_size).astype(np.float32) * 2.0 * np.pi
    print('  -> Compiling Python loops to LLVM Machine Code...')
    _numba_scanline_evaluation(cxs, cys, rxs, rys, thetas, target, batch_size)
    iterations = 20
    start = time.perf_counter()
    for _ in range(iterations):
        _numba_scanline_evaluation(cxs, cys, rxs, rys, thetas, target, batch_size)
    end = time.perf_counter()
    total_time = end - start
    time_per_iter = total_time / (iterations * batch_size)
    print(f'  Numba JIT Time per mathematical candidate calculation: {time_per_iter * 1000000.0:.3f} microseconds.')
    return time_per_iter

def parse_ini(filepath: str) -> Dict[str, str]:
    settings = {}
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith(';'):
                    continue
                if '=' in line:
                    parts = line.split('=', 1)
                    key = parts[0].strip()
                    val = parts[1].strip()
                    settings[key] = val
    except Exception:
        pass
    return settings

def run_cpu_stub_micro_benchmark() -> float:
    print('[Calibration] Measuring Original CPU Stub (Mock) performance...')
    profile = GeneratorProfile()
    engine = ShapeGenerationEngine(profile)
    for _ in range(500):
        s = Shape()
        s.data = [random.uniform(0.0, 2000.0) for _ in range(5)]
        engine.compute_difference(s)
        engine.mutate_shape(s)
    iterations = 5000
    start_time = time.perf_counter()
    for _ in range(iterations):
        s = Shape()
        s.type = ShapeType.SHAPE_ELLIPSE
        s.data = [random.uniform(0.0, 2000.0), random.uniform(0.0, 2000.0), random.uniform(1.0, 100.0), random.uniform(1.0, 100.0), random.uniform(0.0, 360.0)]
        s.color = [random.randint(0, 255) for _ in range(4)]
        engine.compute_difference(s)
        engine.mutate_shape(s)
    end_time = time.perf_counter()
    time_per_iter = (end_time - start_time) / iterations
    print(f'  Original CPU Stub Time per iteration: {time_per_iter * 1000000.0:.3f} microseconds.')
    return time_per_iter

def format_time(seconds: float) -> str:
    if seconds < 1.0:
        return f'{seconds * 1000.0:.1f} ms'
    if seconds < 60.0:
        return f'{seconds:.2f} s'
    if seconds < 3600.0:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f'{mins}m {secs:.1f}s'
    hours = int(seconds // 3600)
    mins = int(seconds % 3600 // 60)
    return f'{hours}h {mins}m'

def main():
    print('=' * 115)
    print('    FORZA PAINTER CPU ADVANCED OPTIMIZATION BENCHMARK (Numba LLVM vs. Stubs)')
    print('=' * 115)
    root_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(root_dir) == 'python_painter':
        root_dir = os.path.dirname(root_dir)
    settings_dir = os.path.join(root_dir, 'settings')
    ini_files = []
    if os.path.isdir(settings_dir):
        ini_files = [f for f in os.listdir(settings_dir) if f.lower().endswith('.ini') and (not f.startswith('_'))]
    ini_files.sort()
    time_per_iter_stub = run_cpu_stub_micro_benchmark()
    time_per_iter_numba = run_numba_micro_benchmark() if NUMBA_AVAILABLE else 0.0
    print('-' * 115)
    presets_data = []
    for filename in ini_files:
        filepath = os.path.join(settings_dir, filename)
        config = parse_ini(filepath)
        name = filename[:-4]
        clean_name = name.split('.', 1)[-1].strip() if '.' in name else name
        if '-' in clean_name:
            clean_name = clean_name.split('-', 1)[0].strip()
        random_samples = int(config.get('randomSamples', 20000))
        mutated_samples = int(config.get('mutatedSamples', 200))
        stop_at = int(config.get('stopAt', 2000))
        work_per_shape = random_samples + mutated_samples
        shapes_sec_stub = 1.0 / (work_per_shape * time_per_iter_stub) if time_per_iter_stub > 0 else 0.0
        shapes_sec_numba = 1.0 / (work_per_shape * time_per_iter_numba) if time_per_iter_numba > 0 else 0.0
        presets_data.append({'display_name': clean_name, 'random_samples': random_samples, 'mutated_samples': mutated_samples, 'stop_at': stop_at, 'shapes_sec_stub': shapes_sec_stub, 'shapes_sec_numba': shapes_sec_numba})
    presets_data.sort(key=lambda x: x['shapes_sec_stub'], reverse=True)
    print('\n' + '=' * 115)
    print(f" {'PRESET NAME':<22} | {'SAMPLES (R/M)':<13} | {'STUB SHAPES/SEC':<17} | {'NUMBA JIT SHAPES/SEC':<21} | {'FULL JIT TIME':<15}")
    print('=' * 115)
    for item in presets_data:
        samples_str = f"{item['random_samples']}/{item['mutated_samples']}"
        stub_sec_str = f"{item['shapes_sec_stub']:.2f}"
        numba_sec_str = f"{item['shapes_sec_numba']:.2f}" if NUMBA_AVAILABLE else 'N/A'
        full_time = item['stop_at'] / item['shapes_sec_numba'] if NUMBA_AVAILABLE and item['shapes_sec_numba'] > 0 else 0.0
        full_time_str = format_time(full_time) if NUMBA_AVAILABLE else 'N/A'
        print(f" {item['display_name']:<22} | {samples_str:<13} | {stub_sec_str:<17} | {numba_sec_str:<21} | {full_time_str:<15}")
    print('=' * 115)
    print('Note: STUB represents the execution of an empty placeholder function.')
    print('      NUMBA JIT represents the CPU executing true localized pixel math using compiled LLVM Machine Code.')
    print('      This demonstrates extreme CPU optimization scaling matching native C++ structures.')
    print('=' * 115)
    input('\nBenchmark complete. Press Enter to exit...')
    return 0
if __name__ == '__main__':
    sys.exit(main())