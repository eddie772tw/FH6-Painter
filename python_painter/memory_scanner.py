import ctypes
from ctypes import wintypes
import struct
import os
import time
from typing import List, Tuple, Optional
PROCESS_VM_READ = 16
PROCESS_VM_WRITE = 32
PROCESS_VM_OPERATION = 8
PROCESS_QUERY_INFORMATION = 1024
PROCESS_QUERY_LIMITED_INFORMATION = 4096
MEM_COMMIT = 4096
MEM_PRIVATE = 131072
PAGE_NOACCESS = 1
PAGE_READONLY = 2
PAGE_READWRITE = 4
PAGE_WRITECOPY = 8
PAGE_EXECUTE_READ = 32
PAGE_EXECUTE_READWRITE = 64
PAGE_EXECUTE_WRITECOPY = 128
PAGE_GUARD = 256
TH32CS_SNAPPROCESS = 2
CHUNK_SIZE = 4 * 1024 * 1024

class MemoryOffsets:
    GROUP_COUNT_OFFSET = 90
    GROUP_TABLE_OFFSET = 120
    LAYER_POS_OFFSET = 24
    LAYER_SCALE_OFFSET = 40
    LAYER_ROTATION_OFFSET = 80
    LAYER_COLOR_OFFSET = 116
    LAYER_MASK_OFFSET = 120
    LAYER_SHAPE_ID_OFFSET = 122
    SHAPE_ID_OTHER = 101
    SHAPE_ID_ELLIPSE = 102

class MEMORY_BASIC_INFORMATION64(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_uint64), ('AllocationBase', ctypes.c_uint64), ('AllocationProtect', ctypes.c_uint32), ('__alignment1', ctypes.c_uint32), ('RegionSize', ctypes.c_uint64), ('State', ctypes.c_uint32), ('Protect', ctypes.c_uint32), ('Type', ctypes.c_uint32), ('__alignment2', ctypes.c_uint32)]

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_void_p), ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD), ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', wintypes.LONG), ('dwFlags', wintypes.DWORD), ('szExeFile', ctypes.c_char * 260)]
kernel32 = ctypes.windll.kernel32
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.ReadProcessMemory.restype = wintypes.BOOL
kernel32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.WriteProcessMemory.restype = wintypes.BOOL
kernel32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(MEMORY_BASIC_INFORMATION64), ctypes.c_size_t]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t
kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Process32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
kernel32.Process32First.restype = wintypes.BOOL
kernel32.Process32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
kernel32.Process32Next.restype = wintypes.BOOL

def find_process_by_name(process_name: str) -> Optional[int]:
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == wintypes.HANDLE(-1).value or snapshot is None:
        return None
    pe = PROCESSENTRY32()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
    if not kernel32.Process32First(snapshot, ctypes.byref(pe)):
        kernel32.CloseHandle(snapshot)
        return None
    try:
        while True:
            exe_name = pe.szExeFile.decode('utf-8', errors='ignore').lower()
            if exe_name == process_name.lower():
                pid = pe.th32ProcessID
                kernel32.CloseHandle(snapshot)
                return pid
            if not kernel32.Process32Next(snapshot, ctypes.byref(pe)):
                break
    except Exception:
        pass
    kernel32.CloseHandle(snapshot)
    return None

def is_user_pointer(address: int) -> bool:
    return 16777216 <= address <= 140737488355328

def is_readable(protect: int) -> bool:
    if protect & PAGE_GUARD or protect & PAGE_NOACCESS:
        return False
    return bool(protect & (PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY))

def is_writable(protect: int) -> bool:
    if protect & PAGE_GUARD or protect & PAGE_NOACCESS:
        return False
    return bool(protect & (PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY))

def read_memory(handle: wintypes.HANDLE, address: int, size: int) -> Optional[bytes]:
    buffer = ctypes.create_string_buffer(size)
    bytes_read = ctypes.c_size_t(0)
    if kernel32.ReadProcessMemory(handle, ctypes.c_void_p(address), buffer, size, ctypes.byref(bytes_read)):
        if bytes_read.value == size:
            return buffer.raw
        return buffer.raw[:bytes_read.value]
    return None

def write_memory(handle: wintypes.HANDLE, address: int, data: bytes) -> bool:
    bytes_written = ctypes.c_size_t(0)
    size = len(data)
    if kernel32.WriteProcessMemory(handle, ctypes.c_void_p(address), ctypes.c_char_p(data), size, ctypes.byref(bytes_written)):
        return bytes_written.value == size
    return False

def read_u64(handle: wintypes.HANDLE, address: int) -> int:
    data = read_memory(handle, address, 8)
    if data and len(data) == 8:
        return struct.unpack('<Q', data)[0]
    return 0

def read_2_floats(handle: wintypes.HANDLE, address: int) -> Optional[Tuple[float, float]]:
    data = read_memory(handle, address, 8)
    if data and len(data) == 8:
        return struct.unpack('<ff', data)
    return None

def is_finite_in_range(val: float, min_val: float, max_val: float) -> bool:
    import math
    if math.isnan(val) or math.isinf(val):
        return False
    return min_val <= val <= max_val

def score_layer(handle: wintypes.HANDLE, layer_ptr: int) -> int:
    if not is_user_pointer(layer_ptr):
        return 0
    score = 0
    pos = read_2_floats(handle, layer_ptr + MemoryOffsets.LAYER_POS_OFFSET)
    if pos and is_finite_in_range(pos[0], -8192.0, 8192.0) and is_finite_in_range(pos[1], -8192.0, 8192.0):
        score += 1
    scale = read_2_floats(handle, layer_ptr + MemoryOffsets.LAYER_SCALE_OFFSET)
    if scale and is_finite_in_range(abs(scale[0]), 1e-05, 64.0) and is_finite_in_range(abs(scale[1]), 1e-05, 64.0):
        score += 1
    color = read_memory(handle, layer_ptr + MemoryOffsets.LAYER_COLOR_OFFSET, 4)
    if color and len(color) == 4:
        score += 1
    shape_id = read_memory(handle, layer_ptr + MemoryOffsets.LAYER_SHAPE_ID_OFFSET, 1)
    if shape_id and len(shape_id) == 1:
        s_id = shape_id[0]
        if s_id in (MemoryOffsets.SHAPE_ID_OTHER, MemoryOffsets.SHAPE_ID_ELLIPSE):
            score += 1
    mask = read_memory(handle, layer_ptr + MemoryOffsets.LAYER_MASK_OFFSET, 1)
    if mask and len(mask) == 1:
        m_val = mask[0]
        if m_val in (0, 1):
            score += 1
    return score

def enumerate_regions(handle: wintypes.HANDLE) -> List[Tuple[int, int, int, int]]:
    regions = []
    address = 0
    mbi = MEMORY_BASIC_INFORMATION64()
    mbi_size = ctypes.sizeof(MEMORY_BASIC_INFORMATION64)
    while address < 140737488355327:
        result = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address), ctypes.byref(mbi), mbi_size)
        if result == 0:
            break
        if mbi.State == MEM_COMMIT and mbi.Type == MEM_PRIVATE:
            if is_readable(mbi.Protect) and is_writable(mbi.Protect):
                regions.append((mbi.BaseAddress, mbi.RegionSize, mbi.Protect, mbi.Type))
        next_addr = mbi.BaseAddress + mbi.RegionSize
        if next_addr <= address:
            break
        address = next_addr
    return regions

def locate_layer_pointers(handle: wintypes.HANDLE, layer_count: int, max_candidates: int=200000) -> List[int]:
    regions = enumerate_regions(handle)
    regions.sort(key=lambda r: r[1], reverse=True)
    print(f'Scanning {len(regions)} private committed read/write regions...')
    pattern_lo = layer_count & 255
    pattern_hi = layer_count >> 8 & 255
    total_bytes = sum((r[1] for r in regions))
    scanned_bytes = 0
    candidates = 0
    last_progress = time.time()
    for base_addr, size, _, _ in regions:
        offset = 0
        while offset < size:
            to_read = min(CHUNK_SIZE, size - offset)
            chunk_base = base_addr + offset
            data = read_memory(handle, chunk_base, to_read)
            if data and len(data) >= 2:
                pos = 0
                while True:
                    idx = data.find(bytes([pattern_lo, pattern_hi]), pos)
                    if idx == -1 or idx >= len(data) - 1:
                        break
                    candidates += 1
                    if candidates > max_candidates:
                        raise RuntimeError('Exceeded maximum candidate thresholds. Scan aborted.')
                    count_addr = chunk_base + idx
                    if count_addr >= MemoryOffsets.GROUP_COUNT_OFFSET:
                        group_base_addr = count_addr - MemoryOffsets.GROUP_COUNT_OFFSET
                        layer_table_addr = read_u64(handle, group_base_addr + MemoryOffsets.GROUP_TABLE_OFFSET)
                        if is_user_pointer(layer_table_addr):
                            is_confident_table = True
                            sample_size = min(layer_count, 8)
                            for i in range(sample_size):
                                layer_ptr = read_u64(handle, layer_table_addr + i * 8)
                                if score_layer(handle, layer_ptr) < 5:
                                    is_confident_table = False
                                    break
                            if is_confident_table:
                                pointers = []
                                for i in range(layer_count):
                                    pointers.append(read_u64(handle, layer_table_addr + i * 8))
                                return pointers
                    pos = idx + 1
            scanned_bytes += to_read
            now = time.time()
            if now - last_progress >= 2.0:
                pct = scanned_bytes * 100.0 / total_bytes if total_bytes > 0 else 0.0
                print(f'Scanning progress: {pct:.1f}% | scanned candidates={candidates}')
                last_progress = now
            offset += to_read
    raise RuntimeError(f'Could not find confidence LiveryGroup memory table for layer count: {layer_count}.\nMake sure vinyl editor is active with an ungrouped template containing exactly {layer_count} circles.')

def try_load_cached_pointers(handle: wintypes.HANDLE, cache_path: str, pid: int, layer_count: int) -> Optional[List[int]]:
    if not os.path.exists(cache_path):
        print('No layer table cache exists. Scan required.')
        return None
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        if len(lines) < 2:
            return None
        header = lines[0].split('|')
        if len(header) != 2:
            return None
        cached_pid = int(header[0])
        cached_layers = int(header[1])
        if cached_pid != pid or cached_layers != layer_count:
            return None
        pointers = []
        for line in lines[1:]:
            pointers.append(int(line, 16))
        if len(pointers) != layer_count:
            return None
        valid_count = 0
        for ptr in pointers:
            if score_layer(handle, ptr) >= 5:
                valid_count += 1
        if valid_count < layer_count * 95 // 100:
            print(f'[Cache] Only {valid_count}/{layer_count} pointers validated. Invaliding pointer cache.')
            return None
        print(f'[Cache] Successfully verified {valid_count}/{layer_count} cached layer pointers.')
        return pointers
    except Exception as e:
        print(f'[Cache] Error reading cache file: {e}')
        return None

def save_cached_pointers(cache_path: str, pid: int, layer_count: int, pointers: List[int]) -> None:
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(f'{pid}|{layer_count}\n')
            for ptr in pointers:
                f.write(f'{ptr:X}\n')
    except Exception as e:
        print(f'[Cache] Failed to write cache: {e}')

def write_shape_to_memory(handle: wintypes.HANDLE, layer_ptr: int, shape_data: dict, canvas_w: float, canvas_h: float, scale_divisor: float, coordinate_scale: float) -> bool:
    data_list = shape_data.get('data', [])
    if len(data_list) < 4:
        return False
    x = float((data_list[0] - canvas_w / 2.0) * coordinate_scale)
    y = float((data_list[1] - canvas_h / 2.0) * coordinate_scale)
    sx = float(data_list[2] / scale_divisor)
    sy = float(data_list[3] / scale_divisor)
    angle = 0.0
    if len(data_list) >= 5:
        angle = float(data_list[4] % 360.0)
        if angle < 0.0:
            angle += 360.0
    pos_bytes = struct.pack('<ff', x, -y)
    write_memory(handle, layer_ptr + MemoryOffsets.LAYER_POS_OFFSET, pos_bytes)
    scale_bytes = struct.pack('<ff', sx, sy)
    write_memory(handle, layer_ptr + MemoryOffsets.LAYER_SCALE_OFFSET, scale_bytes)
    final_angle = (360.0 - angle) % 360.0
    rot_bytes = struct.pack('<f', final_angle)
    write_memory(handle, layer_ptr + MemoryOffsets.LAYER_ROTATION_OFFSET, rot_bytes)
    color_list = shape_data.get('color', [255, 255, 255, 255])
    r = max(0, min(255, int(color_list[0])))
    g = max(0, min(255, int(color_list[1])))
    b = max(0, min(255, int(color_list[2])))
    a = max(0, min(255, int(color_list[3] if len(color_list) >= 4 else 255)))
    color_bytes = struct.pack('4B', r, g, b, a)
    write_memory(handle, layer_ptr + MemoryOffsets.LAYER_COLOR_OFFSET, color_bytes)
    write_memory(handle, layer_ptr + MemoryOffsets.LAYER_SHAPE_ID_OFFSET, bytes([MemoryOffsets.SHAPE_ID_ELLIPSE]))
    write_memory(handle, layer_ptr + MemoryOffsets.LAYER_MASK_OFFSET, bytes([0]))
    return True