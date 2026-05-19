import os
import sys
import time
import math
import random
from typing import Dict, Any, List
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.dirname(current_dir))
PYTORCH_AVAILABLE = False
DIRECTML_AVAILABLE = False
CUDA_AVAILABLE = False
try:
    import torch
    PYTORCH_AVAILABLE = True
    if torch.cuda.is_available():
        CUDA_AVAILABLE = True
except ImportError:
    pass
try:
    import torch_directml
    if torch_directml.is_available():
        DIRECTML_AVAILABLE = True
except ImportError:
    pass
try:
    from generator import Shape, ShapeGenerationEngine, GeneratorProfile, ShapeType
except ImportError:
    try:
        from python_painter.generator import Shape, ShapeGenerationEngine, GeneratorProfile, ShapeType
    except ImportError:
        print('[Error] Could not import python_painter modules. Make sure the package exists.')
        sys.exit(1)

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

def run_single_calibration_batch(device_name: str, num_batches: int, batch_size: int=500) -> float:
    if device_name == 'directml':
        device = torch_directml.device()
    else:
        device = torch.device(device_name)
    target = torch.randn(1, 1, 256, 256, device=device)
    y_g, x_g = torch.meshgrid(torch.linspace(-1.0, 1.0, 256, device=device), torch.linspace(-1.0, 1.0, 256, device=device), indexing='ij')
    x_grid = x_g.unsqueeze(0)
    y_grid = y_g.unsqueeze(0)
    with torch.no_grad():
        cx_w = torch.rand(10, 1, 1, device=device)
        cy_w = torch.rand(10, 1, 1, device=device)
        rx_w = torch.rand(10, 1, 1, device=device)
        ry_w = torch.rand(10, 1, 1, device=device)
        theta_w = torch.rand(10, 1, 1, device=device)
        dx_w = x_grid - cx_w
        dy_w = y_grid - cy_w
        _ = ((dx_w * torch.cos(theta_w) + dy_w * torch.sin(theta_w)) / rx_w) ** 2
    if device_name == 'cuda':
        torch.cuda.synchronize(device)
    elif device_name == 'directml':
        _ = target.cpu()
    start_time = time.perf_counter()
    with torch.no_grad():
        for _ in range(num_batches):
            cx = torch.rand(batch_size, 1, 1, device=device) * 2.0 - 1.0
            cy = torch.rand(batch_size, 1, 1, device=device) * 2.0 - 1.0
            rx = torch.rand(batch_size, 1, 1, device=device) * 0.4 + 0.05
            ry = torch.rand(batch_size, 1, 1, device=device) * 0.4 + 0.05
            theta = torch.rand(batch_size, 1, 1, device=device) * 2.0 * math.pi
            cos_t = torch.cos(theta)
            sin_t = torch.sin(theta)
            dx = x_grid - cx
            dy = y_grid - cy
            x_prime = dx * cos_t + dy * sin_t
            y_prime = -dx * sin_t + dy * cos_t
            dist = (x_prime / rx) ** 2 + (y_prime / ry) ** 2
            masks = (dist <= 1.0).float()
            diff = masks.unsqueeze(1) - target
            losses = torch.mean(diff ** 2, dim=[1, 2, 3])
            _ = torch.argmin(losses)
        if device_name == 'cuda':
            torch.cuda.synchronize(device)
        elif device_name == 'directml':
            _ = losses[0].cpu()
    end_time = time.perf_counter()
    total_time = end_time - start_time
    return total_time / num_batches

def main():
    print('=' * 115)
    print('    FORZA PAINTER UNIFIED CPU vs. GPU SHAPES/SEC BENCHMARK (DirectML / CUDA vs. CPU Stubs & CPU Math)')
    print('=' * 115)
    if not PYTORCH_AVAILABLE:
        print('[Error] PyTorch is not installed in the virtual environment.')
        print('Please run: pip install torch torchvision')
        return 1
    gpu_backend = None
    if DIRECTML_AVAILABLE:
        gpu_backend = 'directml'
        gpu_name = 'DIRECTML (DirectX 12)'
    elif CUDA_AVAILABLE:
        gpu_backend = 'cuda'
        gpu_name = 'CUDA (NVIDIA/AMD)'
    if not gpu_backend:
        print('[Error] No active GPU backend (DirectML or CUDA) was found on the system.')
        print('Please ensure torch-directml is installed or CUDA GPU drivers are active.')
        return 1
    print(f'PyTorch Version: {torch.__version__}')
    print(f'Detected GPU Accelerator: {gpu_name}')
    print('-' * 115)
    print('[Calibration] Measuring Original CPU Stub speed (5,000 iterations)...')
    profile_stub = GeneratorProfile()
    engine_stub = ShapeGenerationEngine(profile_stub)
    for _ in range(200):
        s = Shape()
        s.data = [random.uniform(0.0, 2000.0) for _ in range(5)]
        engine_stub.compute_difference(s)
        engine_stub.mutate_shape(s)
    start_stub = time.perf_counter()
    for _ in range(5000):
        s = Shape()
        s.data = [random.uniform(0.0, 2000.0) for _ in range(5)]
        engine_stub.compute_difference(s)
        engine_stub.mutate_shape(s)
    end_stub = time.perf_counter()
    stub_time_per_iter = (end_stub - start_stub) / 5000.0
    print(f'  Original CPU Stub Time per check: {stub_time_per_iter * 1000000.0:.3f} microseconds')
    print('[Calibration] Measuring Real CPU Vectorized Math speed (500 shapes)...')
    cpu_time_per_batch = run_single_calibration_batch('cpu', num_batches=1, batch_size=500)
    print(f'  Real CPU Math Time per 500 shapes batch: {cpu_time_per_batch * 1000.0:.1f} ms')
    print('[Calibration] Measuring GPU Vectorized Math speed (5,000 shapes)...')
    gpu_time_per_batch = run_single_calibration_batch(gpu_backend, num_batches=10, batch_size=500)
    print(f'  GPU Math Time per 500 shapes batch: {gpu_time_per_batch * 1000.0:.1f} ms')
    print('-' * 115)
    root_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(root_dir) == 'python_painter':
        root_dir = os.path.dirname(root_dir)
    settings_dir = os.path.join(root_dir, 'settings')
    if not os.path.isdir(settings_dir):
        print(f'[Error] Settings directory not found at: {settings_dir}')
        return 1
    ini_files = []
    for filename in os.listdir(settings_dir):
        if filename.lower().endswith('.ini') and (not filename.startswith('_')):
            ini_files.append(filename)
    if not ini_files:
        print('[Error] No preset INI files located inside settings/ directory.')
        return 1
    ini_files.sort()
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
        batches_per_shape = work_per_shape / 500.0
        orig_cpu_time_per_shape = work_per_shape * stub_time_per_iter
        orig_cpu_shapes_sec = 1.0 / orig_cpu_time_per_shape if orig_cpu_time_per_shape > 0 else 0.0
        real_cpu_time_per_shape = batches_per_shape * cpu_time_per_batch
        real_cpu_shapes_sec = 1.0 / real_cpu_time_per_shape if real_cpu_time_per_shape > 0 else 0.0
        gpu_time_per_shape = batches_per_shape * gpu_time_per_batch
        gpu_shapes_sec = 1.0 / gpu_time_per_shape if gpu_time_per_shape > 0 else 0.0
        presets_data.append({'display_name': clean_name, 'random_samples': random_samples, 'mutated_samples': mutated_samples, 'orig_cpu_shapes_sec': orig_cpu_shapes_sec, 'real_cpu_shapes_sec': real_cpu_shapes_sec, 'gpu_shapes_sec': gpu_shapes_sec})
    presets_data.sort(key=lambda x: x['gpu_shapes_sec'], reverse=True)
    print('\n' + '=' * 118)
    print(f" {'PRESET NAME':<22} | {'SAMPLES (R/M)':<13} | {'ORIG CPU (STUB)':<17} | {'REAL CPU (MATH)':<17} | {'GPU (DIRECTML)':<17} | {'GPU SPEEDUP':<12}")
    print('=' * 118)
    for item in presets_data:
        samples_str = f"{item['random_samples']}/{item['mutated_samples']}"
        orig_cpu_str = f"{item['orig_cpu_shapes_sec']:.2f}"
        real_cpu_str = f"{item['real_cpu_shapes_sec']:.2f}"
        gpu_str = f"{item['gpu_shapes_sec']:.2f}"
        speedup = item['gpu_shapes_sec'] / item['real_cpu_shapes_sec'] if item['real_cpu_shapes_sec'] > 0 else 1.0
        print(f" {item['display_name']:<22} | {samples_str:<13} | {orig_cpu_str:<17} | {real_cpu_str:<17} | {gpu_str:<17} | {speedup:>.1f}x faster")
    print('=' * 118)
    print("Note: 'ORIG CPU (STUB)' runs the placeholder generator stubs (does no canvas pixel calculations).")
    print("      'REAL CPU (MATH)' & 'GPU (DIRECTML)' execute the physical rotated ellipse drawing & pixel-by-pixel L2 loss.")
    print("      'GPU SPEEDUP' shows the physical hardware acceleration factor (GPU vs CPU executing the same math).")
    print('=' * 118)
    print('\n[GPU Math Hardware Speedup Chart (vs. Real CPU Math)]')
    print('-' * 90)
    for item in presets_data:
        speedup = item['gpu_shapes_sec'] / item['real_cpu_shapes_sec'] if item['real_cpu_shapes_sec'] > 0 else 1.0
        bar_len = min(40, int(speedup * 4))
        bar = '█' * bar_len
        print(f" {item['display_name']:<22} | {speedup:>6.1f}x | {bar}")
    print('-' * 90)
    input('\nBenchmark complete. Press Enter to exit...')
    return 0
if __name__ == '__main__':
    sys.exit(main())