import os
import sys
import json
import subprocess
import time
from typing import Tuple, List, Dict, Any
try:
    from python_painter import utils
    from python_painter import memory_scanner
except ImportError:
    import utils
    import memory_scanner

def is_json(path: str) -> bool:
    return path.lower().endswith('.json')

def is_header_shape(s: Dict[str, Any]) -> bool:
    data = s.get('data', [])
    color = s.get('color', [])
    return s.get('type') == 1 and len(data) >= 4 and (abs(data[0]) < 0.0001) and (abs(data[1]) < 0.0001) and (len(color) >= 4) and (color[3] == 0)

def find_canvas(shapes: List[Dict[str, Any]]) -> Tuple[float, float]:
    for s in shapes:
        if is_header_shape(s):
            data = s.get('data', [])
            return (float(data[2]), float(data[3]))
    if shapes and len(shapes[0].get('data', [])) >= 4:
        data = shapes[0].get('data', [])
        return (float(data[2]), float(data[3]))
    return (2000.0, 2000.0)

def count_importable_shapes(shapes: List[Dict[str, Any]], include_header: bool=False) -> int:
    count = 0
    for s in shapes:
        if not include_header and is_header_shape(s):
            continue
        if len(s.get('data', [])) >= 4:
            count += 1
    return count

def pick_template_layer_count(shapes: List[Dict[str, Any]]) -> int:
    importable_shapes = count_importable_shapes(shapes)
    if importable_shapes <= 1500:
        return 1500
    if importable_shapes <= 2000:
        return 2000
    return 3000

def ask_layer_count(path: str, recommended: int, is_json_file: bool) -> int:
    print()
    print('=' * 60)
    print(f'File: {os.path.basename(path)}')
    if is_json_file:
        print(f'Detected JSON recommendation: {recommended} layers')
    print('FH6 Surface Limits: front/rear bumper 1000, left/right/top up to 3000.')
    print('=' * 60)
    try:
        user_input = input(f'How many layers? [default {recommended}, allowed 500-3000]: ').strip()
        if not user_input:
            return recommended
        value = int(user_input)
        if value < 500:
            value = 500
        if value > 3000:
            value = 3000
        return value
    except ValueError:
        return recommended

def handle_json_import(json_path: str) -> int:
    print(f'[Importer] Loading shapes from: {json_path}')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            root = json.load(f)
    except Exception as e:
        print(f'[Error] Failed to parse JSON file: {e}')
        return 1
    all_shapes = root.get('shapes', [])
    if not all_shapes:
        print('[Error] No shapes found in JSON file.')
        return 1
    canvas_w, canvas_h = find_canvas(all_shapes)
    recommended = pick_template_layer_count(all_shapes)
    layer_count = ask_layer_count(json_path, recommended, True)
    process_names = ['forzahorizon6.exe', 'forzahorizon5.exe']
    pid = None
    active_process_name = ''
    for name in process_names:
        pid = memory_scanner.find_process_by_name(name)
        if pid is not None:
            active_process_name = name
            break
    if pid is None:
        print('[Error] Neither Forza Horizon 6 nor Forza Horizon 5 process is currently running.')
        print('Please launch the game and open the vinyl group editor before importing.')
        return 1
    print(f"[Process] Found process '{active_process_name}' with PID={pid}")
    handle = memory_scanner.kernel32.OpenProcess(memory_scanner.PROCESS_QUERY_INFORMATION | memory_scanner.PROCESS_QUERY_LIMITED_INFORMATION | memory_scanner.PROCESS_VM_READ | memory_scanner.PROCESS_VM_WRITE | memory_scanner.PROCESS_VM_OPERATION, False, pid)
    if not handle:
        print(f'[Error] OpenProcess failed. Win32 Error Code: {memory_scanner.kernel32.GetLastError()}')
        return 1
    try:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_path = os.path.join(root_dir, 'fh6-layer-table.cache')
        pointers = memory_scanner.try_load_cached_pointers(handle, cache_path, pid, layer_count)
        if pointers is None:
            print('[Scanner] Cache invalid or missing. Initiating active game memory scan...')
            pointers = memory_scanner.locate_layer_pointers(handle, layer_count)
            memory_scanner.save_cached_pointers(cache_path, pid, layer_count, pointers)
            print('[Scanner] Active game memory scan completed successfully. Pointer cache updated.')
        print(f'[Scanner] Target LiveryGroup resolved. Active template layers={len(pointers)}')
        shapes_to_import = []
        for s in all_shapes:
            if is_header_shape(s):
                continue
            if len(s.get('data', [])) >= 4:
                shapes_to_import.append(s)
        n_to_write = min(len(shapes_to_import), len(pointers))
        print(f'[Importer] Injecting {n_to_write} shapes into game memory...')
        written = 0
        scale_divisor = 63.0 if 'horizon6' in active_process_name else 100.0
        for i in range(n_to_write):
            layer_ptr = pointers[i]
            if memory_scanner.score_layer(handle, layer_ptr) < 5:
                continue
            success = memory_scanner.write_shape_to_memory(handle, layer_ptr, shapes_to_import[i], canvas_w, canvas_h, scale_divisor, coordinate_scale=1.0)
            if success:
                written += 1
                if written <= 12 or written % 100 == 0:
                    print(f'  [written {written}/{n_to_write}] -> layerPtr=0x{layer_ptr:X}')
        print(f'[Complete] Successfully injected {written}/{n_to_write} vinyl layers into game process memory.')
        if len(shapes_to_import) > len(pointers):
            print('[Warning] JSON file contains more shapes than target template layers. Remaining shapes were skipped.')
    except Exception as e:
        print(f'[Error] Memory scanner injection failed: {e}')
        import traceback
        traceback.print_exc()
        return 1
    finally:
        memory_scanner.kernel32.CloseHandle(handle)
    return 0

def handle_image_generation(img_path: str) -> int:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    layer_count = ask_layer_count(img_path, 2000, False)
    print()
    print('=' * 60)
    print('Select Generator Engine:')
    print('  [1] Native C++ Generator (used in OG Forza Painter and Geometrize-lib)')
    print('  [2] GPU Accelerated Generator (Support both NVIDIA CUDA and AMD ROCm)')
    print('  [3] Python Numba JIT Generator (Fastest in most rigs)')
    print('=' * 60)
    engine_choice = '3'
    try:
        user_choice = input('Choose engine [1, 2, or 3, default 3]: ').strip()
        if user_choice in ('1', '2', '3'):
            engine_choice = user_choice
    except Exception:
        pass
    img_dir = os.path.dirname(img_path)
    img_name = os.path.splitext(os.path.basename(img_path))[0]
    output_json = os.path.join(img_dir, f'{img_name}.json')
    if engine_choice == '1':
        original_painter = os.path.join(root_dir, 'forza-painter.exe')
        if not os.path.exists(original_painter):
            print(f'[Error] Original C++ generator not found at: {original_painter}')
            return 1
        utils.update_profiles_for_layer_count(root_dir, layer_count)
        print(f'[Generator] Launching native C++ generator for image: {img_path}')
        try:
            proc = subprocess.run([original_painter, img_path], cwd=root_dir)
            return proc.returncode
        except Exception as e:
            print(f'[Error] Failed to start C++ generator: {e}')
            return 1
    else:
        print()
        print('=' * 60)
        print('Select Quality Preset:')
        print('  [1] Fastest (500 random / 80 mutated) - For Previewing or Roughing Out')
        print('  [2] Fast (2000 random / 100 mutated)')
        print('  [3] Balanced (5000 random / 500 mutated) - Recommended')
        print('  [4] Quality (15000 random / 500 mutated)')
        print('  [5] High Quality (50000 random / 500 mutated) - Use at your own risk!')
        print('=' * 60)
        preset_choice = '3'
        try:
            user_choice = input('Choose preset [1-5, default 3]: ').strip()
            if user_choice in ('1', '2', '3', '4', '5'):
                preset_choice = user_choice
        except Exception:
            pass
        samples_mapping = {'1': (500, 80), '2': (2000, 100), '3': (5000, 500), '4': (15000, 500), '5': (50000, 500)}
        random_samples, mutated_samples = samples_mapping[preset_choice]
        success = False
        if engine_choice == '2':
            gpu_backend = 'cpu'
            try:
                import torch
                import torch_directml
                if torch_directml.is_available():
                    gpu_backend = 'directml'
                elif torch.cuda.is_available():
                    gpu_backend = 'cuda'
            except ImportError:
                print('[Warning] PyTorch or DirectML not found. GPU solver falling back to CPU.')
            print(f'[GPU Solver] Initializing on device: {gpu_backend.upper()}')
            try:
                try:
                    from python_painter import gpu_generator
                except ImportError:
                    import gpu_generator
                solver = gpu_generator.GPUImageGenerator(gpu_backend, random_samples, mutated_samples)
                success = solver.optimize_image(img_path, layer_count, output_json)
            except Exception as e:
                print(f'[Error] GPU shape generation failed: {e}')
                import traceback
                traceback.print_exc()
                return 1
        elif engine_choice == '3':
            try:
                try:
                    from python_painter import numba_generator
                except ImportError:
                    import numba_generator
                solver = numba_generator.NumbaImageGenerator(random_samples, mutated_samples)
                success = solver.optimize_image(img_path, layer_count, output_json)
            except Exception as e:
                print(f'[Error] Numba JIT shape generation failed: {e}')
                import traceback
                traceback.print_exc()
                return 1
        if success:
            print(f'\n[Success] Shape optimization completed successfully.')
            return 0
        else:
            return 1

def main() -> int:
    if len(sys.argv) < 2:
        print('+' * 80)
        print(' Forza Painter Python Migration Edition')
        print('+' * 80)
        print('Usage:')
        print('  Image to JSON: Drag-and-drop PNG/JPG files onto this script.')
        print('  JSON to Game: Drag-and-drop generated JSON files onto this script.')
        print('\nNote: Make sure Forza Horizon is running with the vinyl group editor active.')
        print('+' * 80)
        input('\nPress Enter to close...')
        return 2
    exit_code = 0
    for path in sys.argv[1:]:
        if not os.path.exists(path):
            print(f'[Error] Copy the file to this folder and try again!')
            exit_code = 1
            continue
        if is_json(path):
            exit_code = handle_json_import(path)
        else:
            exit_code = handle_image_generation(path)
        if exit_code != 0:
            break
    if exit_code != 0:
        input('\nAn error occurred. Press Enter to close...')
    return exit_code
if __name__ == '__main__':
    sys.exit(main())