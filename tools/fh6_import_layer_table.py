#!/usr/bin/env python3
import sys
import os
import time
import math
import struct
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import ctypes
from ctypes import wintypes

# --- Win32 API Constants ---
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000

PAGE_NOACCESS = 0x01
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80
PAGE_GUARD = 0x100

TH32CS_SNAPPROCESS = 0x00000002

# --- FH6 Memory Offsets & Structs ---
GROUP_COUNT_OFFSET = 0x5A
GROUP_TABLE_OFFSET = 0x78

LAYER_POS_OFFSET = 0x18
LAYER_SCALE_OFFSET = 0x28
LAYER_ROTATION_OFFSET = 0x50
LAYER_COLOR_OFFSET = 0x74
LAYER_MASK_OFFSET = 0x78
LAYER_SHAPE_ID_OFFSET = 0x7A

SHAPE_ID_OTHER = 101
SHAPE_ID_ELLIPSE = 102

CHUNK_SIZE = 4 * 1024 * 1024

class MEMORY_BASIC_INFORMATION64(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_uint64),
        ("AllocationBase", ctypes.c_uint64),
        ("AllocationProtect", ctypes.c_uint32),
        ("__alignment1", ctypes.c_uint32),
        ("RegionSize", ctypes.c_uint64),
        ("State", ctypes.c_uint32),
        ("Protect", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
        ("__alignment2", ctypes.c_uint32)
    ]

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_char * 260)
    ]

# --- Win32 ctypes Function Setup ---
kernel32 = ctypes.windll.kernel32

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

kernel32.ReadProcessMemory.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t)
]
kernel32.ReadProcessMemory.restype = wintypes.BOOL

kernel32.WriteProcessMemory.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t)
]
kernel32.WriteProcessMemory.restype = wintypes.BOOL

kernel32.VirtualQueryEx.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION64),
    ctypes.c_size_t
]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t

kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE

kernel32.Process32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
kernel32.Process32First.restype = wintypes.BOOL

kernel32.Process32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
kernel32.Process32Next.restype = wintypes.BOOL

# --- Numba JIT Compilation & Fallbacks ---
HAS_NUMBA = False
try:
    import numba
    HAS_NUMBA = True
except ImportError:
    pass

if HAS_NUMBA:
    @numba.jit(nopython=True, fastmath=True, cache=True)
    def numba_scan_chunk(data, pattern_lo, pattern_hi):
        """High-performance JIT-compiled scanner that runs at native C speed."""
        indices = []
        n = len(data)
        for i in range(n - 1):
            if data[i] == pattern_lo and data[i+1] == pattern_hi:
                indices.append(i)
        return indices
else:
    def python_scan_chunk(data, pattern_lo, pattern_hi):
        """Optimized fallback scanner utilizing native C implementation of bytes.find()."""
        indices = []
        pattern = bytes([pattern_lo, pattern_hi])
        pos = data.find(pattern)
        while pos != -1:
            indices.append(pos)
            pos = data.find(pattern, pos + 1)
        return indices

# --- Helper Functions ---
def find_forza_process():
    h_snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if h_snapshot == wintypes.HANDLE(-1).value or h_snapshot is None:
        raise OSError("CreateToolhelp32Snapshot failed.")
    
    pe = PROCESSENTRY32()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
    
    pid = None
    if kernel32.Process32First(h_snapshot, ctypes.byref(pe)):
        while True:
            exe_name = pe.szExeFile.decode('utf-8', errors='ignore').lower()
            if exe_name == "forzahorizon6.exe":
                pid = pe.th32ProcessID
                break
            if not kernel32.Process32Next(h_snapshot, ctypes.byref(pe)):
                break
    kernel32.CloseHandle(h_snapshot)
    
    if pid is None:
        raise RuntimeError("forzahorizon6.exe is not running.")
    return pid

def try_read(handle, address, size):
    buf = ctypes.create_string_buffer(size)
    bytes_read = ctypes.c_size_t(0)
    res = kernel32.ReadProcessMemory(handle, ctypes.c_void_p(address), buf, size, ctypes.byref(bytes_read))
    if not res or bytes_read.value == 0:
        return None
    return buf.raw[:bytes_read.value]

def write_bytes(handle, address, data):
    size = len(data)
    buf = ctypes.create_string_buffer(data, size)
    bytes_written = ctypes.c_size_t(0)
    res = kernel32.WriteProcessMemory(handle, ctypes.c_void_p(address), buf, size, ctypes.byref(bytes_written))
    if not res or bytes_written.value != size:
        raise OSError(f"Write failed at 0x{address:X}")

def read_u64(handle, address):
    data = try_read(handle, address, 8)
    if not data or len(data) != 8:
        return 0
    return struct.unpack('<Q', data)[0]

def read_2_floats(handle, address):
    data = try_read(handle, address, 8)
    if not data or len(data) != 8:
        return None
    return struct.unpack('<ff', data)

def is_user_ptr(val):
    return 0x000001000000 < val < 0x800000000000

def is_finite_in_range(val, min_val, max_val):
    if math.isnan(val) or math.isinf(val):
        return False
    return min_val <= val <= max_val

def is_readable(protect):
    if (protect & PAGE_GUARD) or (protect & PAGE_NOACCESS):
        return False
    return bool(protect & (PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY))

def is_writable(protect):
    if (protect & PAGE_GUARD) or (protect & PAGE_NOACCESS):
        return False
    return bool(protect & (PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY))

def enumerate_regions(handle):
    regions = []
    address = 0
    mbi = MEMORY_BASIC_INFORMATION64()
    mbi_size = ctypes.sizeof(MEMORY_BASIC_INFORMATION64)
    while address < 0x7FFFFFFFFFFF:
        res = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address), ctypes.byref(mbi), mbi_size)
        if res == 0:
            break
        
        if mbi.State == MEM_COMMIT and mbi.Type == MEM_PRIVATE:
            if is_readable(mbi.Protect) and is_writable(mbi.Protect):
                regions.append({
                    "Base": mbi.BaseAddress,
                    "Size": mbi.RegionSize,
                    "Protect": mbi.Protect,
                    "Type": mbi.Type
                })
        
        next_addr = mbi.BaseAddress + mbi.RegionSize
        if next_addr <= address:
            break
        address = next_addr
    return regions

# --- Layer Assessment Logic ---
def score_layer(handle, layer_ptr):
    if not is_user_ptr(layer_ptr):
        return 0
    score = 0
    pos = read_2_floats(handle, layer_ptr + LAYER_POS_OFFSET)
    if pos is not None and is_finite_in_range(pos[0], -8192.0, 8192.0) and is_finite_in_range(pos[1], -8192.0, 8192.0):
        score += 1
    scale = read_2_floats(handle, layer_ptr + LAYER_SCALE_OFFSET)
    if scale is not None and is_finite_in_range(abs(scale[0]), 0.00001, 64.0) and is_finite_in_range(abs(scale[1]), 0.00001, 64.0):
        score += 1
    color = try_read(handle, layer_ptr + LAYER_COLOR_OFFSET, 4)
    if color is not None and len(color) == 4:
        score += 1
    shape = try_read(handle, layer_ptr + LAYER_SHAPE_ID_OFFSET, 1)
    if shape is not None and len(shape) == 1 and (shape[0] == SHAPE_ID_OTHER or shape[0] == SHAPE_ID_ELLIPSE):
        score += 1
    mask = try_read(handle, layer_ptr + LAYER_MASK_OFFSET, 1)
    if mask is not None and len(mask) == 1 and (mask[0] == 0 or mask[0] == 1):
        score += 1
    return score

def first_sample_is_perfect(handle, table_addr, layer_count):
    sample = min(layer_count, 16)
    for i in range(sample):
        ptr = read_u64(handle, table_addr + i * 8)
        if score_layer(handle, ptr) < 5:
            return False
    return True

def count_valid_layers(handle, table_addr, layer_count):
    # Optimize using a bulk read for the entire pointer table (24KB for 3000 layers)
    table_data = try_read(handle, table_addr, layer_count * 8)
    if not table_data or len(table_data) != layer_count * 8:
        # Fallback to individual reads if bulk read fails
        valid = 0
        for i in range(layer_count):
            ptr = read_u64(handle, table_addr + i * 8)
            if score_layer(handle, ptr) >= 5:
                valid += 1
        return valid
        
    ptrs = struct.unpack(f'<{layer_count}Q', table_data)
    valid = 0
    for ptr in ptrs:
        if score_layer(handle, ptr) >= 5:
            valid += 1
    return valid

# --- Memory Scanning Workers ---
def scan_region_task(handle, region, pattern_lo, pattern_hi):
    candidates = []
    base = region["Base"]
    size = region["Size"]
    offset = 0
    scan_func = numba_scan_chunk if HAS_NUMBA else python_scan_chunk
    
    while offset < size:
        to_read = min(CHUNK_SIZE, size - offset)
        chunk_base = base + offset
        data = try_read(handle, chunk_base, to_read)
        if data and len(data) >= 2:
            matches = scan_func(data, pattern_lo, pattern_hi)
            for pos in matches:
                candidates.append(chunk_base + pos)
        offset += to_read
    return candidates

def pick_best_perfect(handle, perfect, layer_count):
    if not perfect:
        raise ValueError(f"No confident LiveryGroup match. Open FH6 vinyl editor with a fresh ungrouped {layer_count}-sphere template.")
        
    best_table = 0
    best_valid = -1
    for group_addr, table_addr in perfect:
        valid = count_valid_layers(handle, table_addr, layer_count)
        print(f"candidate group=0x{group_addr:X} table=0x{table_addr:X} valid={valid}/{layer_count}")
        if valid > best_valid:
            best_valid = valid
            best_table = table_addr
            
    if best_valid < layer_count * 95 // 100:
        raise ValueError(f"Best LiveryGroup candidate only validated {best_valid}/{layer_count} layers; refusing unsafe write.")
        
    # Read final table in one bulk read
    pointers = []
    table_data = try_read(handle, best_table, layer_count * 8)
    if table_data and len(table_data) == layer_count * 8:
        pointers = list(struct.unpack(f'<{layer_count}Q', table_data))
    else:
        for i in range(layer_count):
            pointers.append(read_u64(handle, best_table + i * 8))
    return pointers

def locate_layer_pointers(handle, layer_count, max_candidates):
    regions = enumerate_regions(handle)
    regions.sort(key=lambda r: r["Size"], reverse=True)
    print(f"Scanning writable private regions={len(regions)}")
    
    pattern_lo = layer_count & 0xFF
    pattern_hi = (layer_count >> 8) & 0xFF
    
    perfect = []
    candidates_count = 0
    total_bytes = sum(r["Size"] for r in regions)
    scanned_bytes = 0
    last_progress_time = time.time()
    
    # ThreadPool for parallel memory scanning across multiple CPU cores
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(scan_region_task, handle, r, pattern_lo, pattern_hi): r for r in regions}
        
        for future in as_completed(futures):
            region = futures[future]
            scanned_bytes += region["Size"]
            
            try:
                matches = future.result()
                for count_addr in matches:
                    if count_addr < GROUP_COUNT_OFFSET:
                        continue
                    candidates_count += 1
                    
                    group_addr = count_addr - GROUP_COUNT_OFFSET
                    table_addr = read_u64(handle, group_addr + GROUP_TABLE_OFFSET)
                    if not is_user_ptr(table_addr):
                        continue
                        
                    if first_sample_is_perfect(handle, table_addr, layer_count):
                        perfect.append((group_addr, table_addr))
                        
            except Exception:
                pass
                
            now = time.time()
            if now - last_progress_time >= 2.0 or len(perfect) > 0:
                pct = 0.0 if total_bytes == 0 else scanned_bytes * 100.0 / total_bytes
                print(f"scan {pct:.1f}% regions candidates={candidates_count} perfect={len(perfect)}")
                last_progress_time = now
                
            if len(perfect) >= 1 or candidates_count > max_candidates:
                break
                
    return pick_best_perfect(handle, perfect, layer_count)

# --- Caching Support ---
def try_load_cached_layer_pointers(handle, cache_path, pid, layer_count):
    if not os.path.exists(cache_path):
        print("No layer cache yet; full scan needed once for this FH6/editor session.")
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        if len(lines) < 2:
            print("Layer cache is incomplete; full scan needed.")
            return None
            
        header = lines[0].split('|')
        if len(header) != 2:
            print("Layer cache header is invalid; full scan needed.")
            return None
            
        cached_pid = int(header[0])
        cached_layers = int(header[1])
        if cached_pid != pid:
            print("Layer cache is from another FH6 process; full scan needed.")
            return None
        if cached_layers != layer_count:
            print("Layer cache is for a different layer count; full scan needed.")
            return None
            
        pointers = []
        for line in lines[1:]:
            pointers.append(int(line, 16))
            if len(pointers) == layer_count:
                break
                
        if len(pointers) != layer_count:
            print("Layer cache pointer count does not match; full scan needed.")
            return None
            
        valid = 0
        for ptr in pointers:
            if score_layer(handle, ptr) >= 5:
                valid += 1
                
        if valid < layer_count * 95 // 100:
            print(f"Layer cache no longer matches the active vinyl group ({valid}/{layer_count} valid); full scan needed.")
            return None
            
        print(f"Using cached layer pointers valid={valid}/{layer_count}")
        return pointers
    except Exception as e:
        print(f"Layer cache could not be read; full scan needed. Error: {e}")
        return None

def save_cached_layer_pointers(cache_path, pid, layer_count, pointers):
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(f"{pid}|{layer_count}\n")
            for ptr in pointers:
                f.write(f"{ptr:X}\n")
    except Exception as e:
        print(f"Failed to save layer cache: {e}")

# --- JSON Loading & Writing ---
def load_shapes(path):
    with open(path, "r", encoding="utf-8") as f:
        root = json.load(f)
    raw_shapes = root.get("shapes", [])
    shapes = []
    for raw in raw_shapes:
        shapes.append({
            "type": int(raw.get("type", 0)),
            "data": [float(x) for x in raw.get("data", [])],
            "color": [int(c) for c in raw.get("color", [])]
        })
    return shapes

def is_header_shape(s):
    return (
        s["type"] == 1
        and len(s["data"]) >= 4
        and abs(s["data"][0]) < 0.0001
        and abs(s["data"][1]) < 0.0001
        and len(s["color"]) >= 4
        and s["color"][3] == 0
    )

def find_canvas(shapes):
    for s in shapes:
        if is_header_shape(s):
            return s["data"][2], s["data"][3]
    if shapes and len(shapes[0]["data"]) >= 4:
        return shapes[0]["data"][2], shapes[0]["data"][3]
    raise ValueError("Could not determine canvas size.")

def build_import_shape_list(all_shapes, include_header):
    shapes = []
    for s in all_shapes:
        if not include_header and is_header_shape(s):
            continue
        if len(s["data"]) >= 4:
            shapes.append(s)
    return shapes

def clamp_byte(val):
    return max(0, min(255, int(val)))

def pack_color(shape):
    r = shape["color"][0] if len(shape["color"]) > 0 else 255
    g = shape["color"][1] if len(shape["color"]) > 1 else 255
    b = shape["color"][2] if len(shape["color"]) > 2 else 255
    return bytes([clamp_byte(r), clamp_byte(g), clamp_byte(b), 255])

def write_shape(handle, layer_ptr, shape, canvas_w, canvas_h, options):
    x = float((shape["data"][0] - canvas_w / 2.0) * options.coord_scale)
    y = float((shape["data"][1] - canvas_h / 2.0) * options.coord_scale)
    sx = float(shape["data"][2] / options.scale_div)
    sy = float(shape["data"][3] / options.scale_div)
    angle = float(shape["data"][4] % 360.0) if len(shape["data"]) >= 5 else 0.0
    
    write_bytes(handle, layer_ptr + LAYER_POS_OFFSET, struct.pack('<ff', x, -y))
    write_bytes(handle, layer_ptr + LAYER_SCALE_OFFSET, struct.pack('<ff', sx, sy))
    write_bytes(handle, layer_ptr + LAYER_ROTATION_OFFSET, struct.pack('<f', (360.0 - angle) % 360.0))
    write_bytes(handle, layer_ptr + LAYER_COLOR_OFFSET, pack_color(shape))
    write_bytes(handle, layer_ptr + LAYER_SHAPE_ID_OFFSET, bytes([SHAPE_ID_ELLIPSE]))
    write_bytes(handle, layer_ptr + LAYER_MASK_OFFSET, bytes([0]))

def print_preview(layer_pointers, shapes, canvas_w, canvas_h, options, count):
    for i in range(count):
        shape_index = len(shapes) - 1 - i if options.reverse else i
        if shape_index >= len(shapes) or i >= len(layer_pointers):
            break
        shape = shapes[shape_index]
        x = (shape["data"][0] - canvas_w / 2.0) * options.coord_scale
        y = (shape["data"][1] - canvas_h / 2.0) * options.coord_scale
        sx = shape["data"][2] / options.scale_div
        sy = shape["data"][3] / options.scale_div
        print(f"#{i + 1} shapeIndex={shape_index} ptr=0x{layer_pointers[i]:X} x={x:.3f} y(write)={-y:.3f} sx={sx:.3f} sy={sy:.3f}")

def run_importer(json_path, layers=3000, dry_run=False, reverse=False, include_header=False, no_cache=False, scale_div=63.0, coord_scale=1.0, max_candidates=200000):
    print(f"Optimization Status: Numba acceleration = {'ENABLED' if HAS_NUMBA else 'DISABLED'}")
    
    # Wrap options in a simple container class to maintain compatibility
    class Options:
        def __init__(self):
            self.json_path = json_path
            self.layers = layers
            self.dry_run = dry_run
            self.reverse = reverse
            self.include_header = include_header
            self.no_cache = no_cache
            self.scale_div = scale_div
            self.coord_scale = coord_scale
            self.max_candidates = max_candidates
            
    options = Options()
    
    try:
        all_shapes = load_shapes(json_path)
        if not all_shapes:
            raise ValueError("No shapes found in JSON.")
            
        canvas_w, canvas_h = find_canvas(all_shapes)
        shapes = build_import_shape_list(all_shapes, include_header)
        if not shapes:
            raise ValueError("No importable shapes found after filtering.")
            
        pid = find_forza_process()
        print(f"PID={pid} JSON shapes={len(shapes)} template layers={layers}")
        print(f"canvas={canvas_w:.3f}x{canvas_h:.3f} scaleDiv={scale_div:.3f} coordScale={coord_scale:.3f} order={'reverse' if reverse else 'table'} dryRun={dry_run}")
        
        access_mask = PROCESS_QUERY_INFORMATION | PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION
        handle = kernel32.OpenProcess(access_mask, False, pid)
        if not handle:
            raise OSError(f"OpenProcess failed. LastError={kernel32.GetLastError()}")
            
        try:
            cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fh6-layer-table.cache")
            layer_pointers = None if no_cache else try_load_cached_layer_pointers(handle, cache_path, pid, layers)
            
            if layer_pointers is None:
                layer_pointers = locate_layer_pointers(handle, layers, max_candidates)
                save_cached_layer_pointers(cache_path, pid, layers, layer_pointers)
                
            print(f"LiveryGroup found. Valid layer pointers={len(layer_pointers)}")
            
            n = min(len(shapes), len(layer_pointers))
            if dry_run:
                print_preview(layer_pointers, shapes, canvas_w, canvas_h, options, min(n, 12))
                print("Dry run only; no writes performed.")
                return 0
                
            written = 0
            for i in range(n):
                shape_index = len(shapes) - 1 - i if reverse else i
                layer_index = i
                layer_ptr = layer_pointers[layer_index]
                
                if score_layer(handle, layer_ptr) < 5:
                    continue
                    
                write_shape(handle, layer_ptr, shapes[shape_index], canvas_w, canvas_h, options)
                written += 1
                if written <= 12 or written % 100 == 0:
                    print(f"written {written}/{n} -> layerPtr=0x{layer_ptr:X}")
                    
            print(f"DONE written={written}/{n}")
            if len(shapes) > len(layer_pointers):
                print("WARNING: JSON has more shapes than template layers. Remaining shapes were skipped.")
                
        finally:
            kernel32.CloseHandle(handle)
            
        return 0
    except Exception as ex:
        print(f"ERROR: {ex}", file=sys.stderr)
        return 1

# --- Main Entry ---
def main():
    parser = argparse.ArgumentParser(description="FH6 Import Layer Table Importer in Python")
    parser.add_argument("json_path", help="Path to input geometry JSON file")
    parser.add_argument("--layers", type=int, default=3000, help="Template layer count")
    parser.add_argument("--dry-run", action="store_true", help="Scan and validate memory without writing")
    parser.add_argument("--reverse", action="store_true", help="Reverse shape order of drawing")
    parser.add_argument("--include-header", action="store_true", help="Include transparent header canvas shape")
    parser.add_argument("--no-cache", action="store_true", help="Ignore and bypass the layer address cache")
    parser.add_argument("--scale-div", type=float, default=63.0, help="Shape scale divisor")
    parser.add_argument("--coord-scale", type=float, default=1.0, help="Coordinate scale multiplier")
    parser.add_argument("--max-candidates", type=int, default=200000, help="Max candidates scanning threshold")
    
    args = parser.parse_args()
    return run_importer(
        json_path=args.json_path,
        layers=args.layers,
        dry_run=args.dry_run,
        reverse=args.reverse,
        include_header=args.include_header,
        no_cache=args.no_cache,
        scale_div=args.scale_div,
        coord_scale=args.coord_scale,
        max_candidates=args.max_candidates
    )

if __name__ == "__main__":
    sys.exit(main())
