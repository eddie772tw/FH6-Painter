#!/usr/bin/env python3
import argparse
import ctypes
import json
import math
import os
import struct
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        ("__alignment2", ctypes.c_uint32),
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
        ("szExeFile", ctypes.c_char * 260),
    ]


# --- Win32 ctypes Function Setup ---
if sys.platform == "win32":
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
        ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.ReadProcessMemory.restype = wintypes.BOOL

    kernel32.WriteProcessMemory.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.WriteProcessMemory.restype = wintypes.BOOL

    kernel32.VirtualQueryEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.POINTER(MEMORY_BASIC_INFORMATION64),
        ctypes.c_size_t,
    ]
    kernel32.VirtualQueryEx.restype = ctypes.c_size_t

    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE

    kernel32.Process32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
    kernel32.Process32First.restype = wintypes.BOOL

    kernel32.Process32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
    kernel32.Process32Next.restype = wintypes.BOOL
else:
    kernel32 = None

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
        for i in range(n - 3):
            if (
                data[i] == pattern_lo
                and data[i + 1] == pattern_hi
                and data[i + 2] == 0
                and data[i + 3] == 0
            ):
                indices.append(i)
        return indices
else:

    def python_scan_chunk(data, pattern_lo, pattern_hi):
        """Optimized fallback scanner utilizing native C implementation of bytes.find()."""
        indices = []
        pattern = bytes([pattern_lo, pattern_hi, 0, 0])
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
            exe_name = pe.szExeFile.decode("utf-8", errors="ignore").lower()
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
    res = kernel32.ReadProcessMemory(
        handle, ctypes.c_void_p(address), buf, size, ctypes.byref(bytes_read)
    )
    if not res or bytes_read.value == 0:
        return None
    return buf.raw[: bytes_read.value]


def write_bytes(handle, address, data):
    size = len(data)
    buf = ctypes.create_string_buffer(data, size)
    bytes_written = ctypes.c_size_t(0)
    res = kernel32.WriteProcessMemory(
        handle, ctypes.c_void_p(address), buf, size, ctypes.byref(bytes_written)
    )
    if not res or bytes_written.value != size:
        raise OSError(f"Write failed at 0x{address:X}")


def read_u64(handle, address):
    data = try_read(handle, address, 8)
    if not data or len(data) != 8:
        return 0
    return struct.unpack("<Q", data)[0]


def read_2_floats(handle, address):
    data = try_read(handle, address, 8)
    if not data or len(data) != 8:
        return None
    return struct.unpack("<ff", data)


def is_user_ptr(val):
    return 0x000001000000 < val < 0x800000000000


def is_finite_in_range(val, min_val, max_val):
    if math.isnan(val) or math.isinf(val):
        return False
    return min_val <= val <= max_val


def is_readable(protect):
    if (protect & PAGE_GUARD) or (protect & PAGE_NOACCESS):
        return False
    return bool(
        protect
        & (
            PAGE_READONLY
            | PAGE_READWRITE
            | PAGE_WRITECOPY
            | PAGE_EXECUTE_READ
            | PAGE_EXECUTE_READWRITE
            | PAGE_EXECUTE_WRITECOPY
        )
    )


def is_writable(protect):
    if (protect & PAGE_GUARD) or (protect & PAGE_NOACCESS):
        return False
    return bool(
        protect
        & (
            PAGE_READWRITE
            | PAGE_WRITECOPY
            | PAGE_EXECUTE_READWRITE
            | PAGE_EXECUTE_WRITECOPY
        )
    )


def enumerate_regions(handle):
    regions = []
    address = 0
    mbi = MEMORY_BASIC_INFORMATION64()
    mbi_size = ctypes.sizeof(MEMORY_BASIC_INFORMATION64)
    while address < 0x7FFFFFFFFFFF:
        res = kernel32.VirtualQueryEx(
            handle, ctypes.c_void_p(address), ctypes.byref(mbi), mbi_size
        )
        if res == 0:
            break

        if mbi.State == MEM_COMMIT and mbi.Type == MEM_PRIVATE:
            if is_readable(mbi.Protect) and is_writable(mbi.Protect):
                regions.append(
                    {
                        "Base": mbi.BaseAddress,
                        "Size": mbi.RegionSize,
                        "Protect": mbi.Protect,
                        "Type": mbi.Type,
                    }
                )

        next_addr = mbi.BaseAddress + mbi.RegionSize
        if next_addr <= address:
            break
        address = next_addr
    return regions


# --- Layer Assessment Logic & Heuristics Manager ---
class StrictnessLevel:
    PERFECT = 1
    RELAXED = 2
    MINIMAL = 3


class HeuristicsManager:
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"successful_regions": [], "last_success_addr": None}

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"[Heuristics] 無法儲存啟發式規則: {e}")

    def record_success(self, group_addr, region):
        self.data["last_success_addr"] = group_addr
        region_info = {
            "size": region["Size"],
            "protect": region["Protect"],
            "offset_ratio": group_addr - region["Base"],
        }
        if region_info not in self.data["successful_regions"]:
            self.data["successful_regions"].append(region_info)
            if len(self.data["successful_regions"]) > 5:
                self.data["successful_regions"].pop(0)
        self.save()


def score_layer_adaptive(handle, layer_ptr, level=StrictnessLevel.PERFECT):
    if not is_user_ptr(layer_ptr):
        return 0
    score = 0

    pos = read_2_floats(handle, layer_ptr + LAYER_POS_OFFSET)
    coord_limit = 8192.0 if level == StrictnessLevel.PERFECT else 32768.0
    if (
        pos is not None
        and is_finite_in_range(pos[0], -coord_limit, coord_limit)
        and is_finite_in_range(pos[1], -coord_limit, coord_limit)
    ):
        score += 1

    scale = read_2_floats(handle, layer_ptr + LAYER_SCALE_OFFSET)
    scale_limit = 64.0 if level == StrictnessLevel.PERFECT else 256.0
    if (
        scale is not None
        and is_finite_in_range(abs(scale[0]), 0.00001, scale_limit)
        and is_finite_in_range(abs(scale[1]), 0.00001, scale_limit)
    ):
        score += 1

    color = try_read(handle, layer_ptr + LAYER_COLOR_OFFSET, 4)
    if color is not None and len(color) == 4:
        score += 1

    shape = try_read(handle, layer_ptr + LAYER_SHAPE_ID_OFFSET, 1)
    if shape is not None and len(shape) == 1:
        if level == StrictnessLevel.PERFECT:
            if shape[0] == SHAPE_ID_OTHER or shape[0] == SHAPE_ID_ELLIPSE:
                score += 1
        else:
            if shape[0] != 0:
                score += 1
            else:
                score += 1

    mask = try_read(handle, layer_ptr + LAYER_MASK_OFFSET, 1)
    if mask is not None and len(mask) == 1:
        if level == StrictnessLevel.PERFECT:
            if mask[0] == 0 or mask[0] == 1:
                score += 1
        else:
            score += 1

    return score


def score_layer(handle, layer_ptr):
    return score_layer_adaptive(handle, layer_ptr, StrictnessLevel.PERFECT)


def first_sample_is_perfect(handle, table_addr, layer_count):
    sample = min(layer_count, 16)
    for i in range(sample):
        ptr = read_u64(handle, table_addr + i * 8)
        if score_layer_adaptive(handle, ptr, StrictnessLevel.PERFECT) < 5:
            return False
    return True


def count_valid_layers_adaptive(handle, table_addr, layer_count, level):
    required_score = (
        5
        if level == StrictnessLevel.PERFECT
        else (3 if level == StrictnessLevel.RELAXED else 2)
    )
    table_data = try_read(handle, table_addr, layer_count * 8)
    if not table_data or len(table_data) != layer_count * 8:
        valid = 0
        for i in range(layer_count):
            ptr = read_u64(handle, table_addr + i * 8)
            if score_layer_adaptive(handle, ptr, level) >= required_score:
                valid += 1
        return valid

    ptrs = struct.unpack(f"<{layer_count}Q", table_data)
    valid = 0
    for ptr in ptrs:
        if score_layer_adaptive(handle, ptr, level) >= required_score:
            valid += 1
    return valid


def count_valid_layers(handle, table_addr, layer_count):
    return count_valid_layers_adaptive(
        handle, table_addr, layer_count, StrictnessLevel.PERFECT
    )


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
        if data and len(data) >= 4:
            matches = scan_func(data, pattern_lo, pattern_hi)
            for pos in matches:
                candidates.append(chunk_base + pos)
        offset += to_read
    return candidates


def pick_best_adaptive(handle, perfect, relaxed, minimal, layer_count):
    if perfect:
        best_table = 0
        best_valid = -1
        best_group = 0
        best_region = None
        for group_addr, table_addr, region in perfect:
            valid = count_valid_layers_adaptive(
                handle, table_addr, layer_count, StrictnessLevel.PERFECT
            )
            print(
                f"[Heuristics] PERFECT 候選組: group=0x{group_addr:X} table=0x{table_addr:X} 有效度={valid}/{layer_count}"
            )
            if valid > best_valid:
                best_valid = valid
                best_table = table_addr
                best_group = group_addr
                best_region = region

        if best_valid >= layer_count * 95 // 100:
            print(f"[Heuristics] 完美匹配成功！有效圖層={best_valid}/{layer_count}")
            return best_group, best_table, best_region, StrictnessLevel.PERFECT

    if relaxed:
        print(
            "\n[Heuristics] PERFECT 匹配度不足或無完美候選，啟用 RELAXED 寬鬆匹配機制..."
        )
        best_table = 0
        best_valid = -1
        best_group = 0
        best_region = None
        for group_addr, table_addr, region in relaxed:
            valid = count_valid_layers_adaptive(
                handle, table_addr, layer_count, StrictnessLevel.RELAXED
            )
            print(
                f"[Heuristics] RELAXED 候選組: group=0x{group_addr:X} table=0x{table_addr:X} 有效度={valid}/{layer_count}"
            )
            if valid > best_valid:
                best_valid = valid
                best_table = table_addr
                best_group = group_addr
                best_region = region

        if best_valid >= layer_count * 80 // 100:
            print(f"[Heuristics] 寬鬆匹配成功！有效圖層={best_valid}/{layer_count}")
            return best_group, best_table, best_region, StrictnessLevel.RELAXED

    if minimal:
        print(
            "\n[Heuristics] RELAXED 匹配度不足或無寬鬆候選，啟用 MINIMAL 極簡保底匹配機制..."
        )
        best_table = 0
        best_valid = -1
        best_group = 0
        best_region = None
        for group_addr, table_addr, region in minimal:
            valid = count_valid_layers_adaptive(
                handle, table_addr, layer_count, StrictnessLevel.MINIMAL
            )
            print(
                f"[Heuristics] MINIMAL 候選組: group=0x{group_addr:X} table=0x{table_addr:X} 有效度={valid}/{layer_count}"
            )
            if valid > best_valid:
                best_valid = valid
                best_table = table_addr
                best_group = group_addr
                best_region = region

        if best_valid >= layer_count * 50 // 100:
            print(f"[Heuristics] 極簡保底匹配成功！有效圖層={best_valid}/{layer_count}")
            return best_group, best_table, best_region, StrictnessLevel.MINIMAL

    raise ValueError(
        f"無任何級別的 LiveryGroup 候選者通過驗證。請在 FH6 中確保已開啟未分組的 {layer_count} 個圓形圖層。"
    )


def locate_layer_pointers(handle, layer_count, max_candidates):
    import threading

    heuristics_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "fh6-heuristics.json"
    )
    heuristics = HeuristicsManager(heuristics_path)

    regions = enumerate_regions(handle)

    def get_region_score(r):
        score = 0
        size = r["Size"]

        for success in heuristics.data.get("successful_regions", []):
            if abs(size - success["size"]) < 4 * 1024 * 1024:  # 誤差在 4MB 內
                score += 1000

        last_addr = heuristics.data.get("last_success_addr")
        if last_addr and r["Base"] <= last_addr <= (r["Base"] + size):
            score += 5000
        elif (
            last_addr and abs(r["Base"] - last_addr) < 512 * 1024 * 1024
        ):  # 512MB 範圍內
            score += 2000

        if 8 * 1024 * 1024 <= size <= 128 * 1024 * 1024:
            score += 100
        else:
            score += size // (1024 * 1024)

        return score

    regions.sort(key=get_region_score, reverse=True)
    print(f"[Heuristics] 啟動記憶體啟發式掃描，總區段數={len(regions)}")

    pattern_lo = layer_count & 0xFF
    pattern_hi = (layer_count >> 8) & 0xFF

    perfect = []
    relaxed = []
    minimal = []

    candidates_count = 0
    non_user_ptr_count = 0
    validation_failed_count = 0
    sample_failures = []

    scan_lock = threading.Lock()

    total_bytes = sum(r["Size"] for r in regions)
    scanned_bytes = 0
    last_progress_time = time.time()

    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(scan_region_task, handle, r, pattern_lo, pattern_hi): r
            for r in regions
        }

        for future in as_completed(futures):
            region = futures[future]
            scanned_bytes += region["Size"]

            try:
                matches = future.result()
                for count_addr in matches:
                    if count_addr < GROUP_COUNT_OFFSET:
                        continue

                    with scan_lock:
                        candidates_count += 1

                    group_addr = count_addr - GROUP_COUNT_OFFSET
                    table_addr = read_u64(handle, group_addr + GROUP_TABLE_OFFSET)
                    if not is_user_ptr(table_addr):
                        with scan_lock:
                            non_user_ptr_count += 1
                        continue

                    sample_len = min(layer_count, 16)
                    is_p = True
                    is_r = True
                    is_m = True

                    sample_scores = []
                    valid_ptrs = True
                    failure_detail = None

                    for i in range(sample_len):
                        ptr = read_u64(handle, table_addr + i * 8)
                        if not is_user_ptr(ptr):
                            valid_ptrs = False
                            failure_detail = (
                                f"圖層 {i} 指針 0x{ptr:X} 不是有效的用戶空間指針"
                            )
                            break

                        sp = score_layer_adaptive(handle, ptr, StrictnessLevel.PERFECT)
                        sr = score_layer_adaptive(handle, ptr, StrictnessLevel.RELAXED)
                        sm = score_layer_adaptive(handle, ptr, StrictnessLevel.MINIMAL)
                        sample_scores.append((sp, sr, sm))

                    if not valid_ptrs or len(sample_scores) < sample_len:
                        is_p = is_r = is_m = False
                    else:
                        is_p = all(s[0] == 5 for s in sample_scores)
                        is_r = sum(1 for s in sample_scores if s[1] >= 3) >= (
                            sample_len - 2
                        )
                        is_m = sum(1 for s in sample_scores if s[2] >= 2) >= (
                            sample_len // 2
                        )

                    with scan_lock:
                        if is_p:
                            perfect.append((group_addr, table_addr, region))
                        elif is_r:
                            relaxed.append((group_addr, table_addr, region))
                        elif is_m:
                            minimal.append((group_addr, table_addr, region))
                        else:
                            validation_failed_count += 1
                            if not failure_detail and sample_scores:
                                failure_detail = f"圖層評分未達標 (最高評分={max(s[0] for s in sample_scores)})"
                            if len(sample_failures) < 5:
                                sample_failures.append(
                                    {
                                        "group_addr": group_addr,
                                        "table_addr": table_addr,
                                        "detail": failure_detail,
                                    }
                                )

            except Exception:
                pass

            now = time.time()
            if now - last_progress_time >= 2.0 or len(perfect) > 0:
                pct = 0.0 if total_bytes == 0 else scanned_bytes * 100.0 / total_bytes
                print(
                    f"掃描進度 {pct:.1f}% candidates={candidates_count} perfect={len(perfect)} relaxed={len(relaxed)}"
                )
                last_progress_time = now

            if len(perfect) >= 1 or candidates_count > max_candidates:
                break

    if not perfect and not relaxed and not minimal:
        print("\n=== 記憶體掃描診斷摘要 ===")
        print(
            f"掃描圖層數量 Pattern: {layer_count} (lo=0x{pattern_lo:02X}, hi=0x{pattern_hi:02X})"
        )
        print(f"記憶體中符合 Pattern 的總候選數: {candidates_count}")
        print(f"  - 無效表指標的候選數: {non_user_ptr_count}")
        print(f"  - 驗證失敗的候選數: {validation_failed_count}")
        if sample_failures:
            print("前幾個候選者的詳細驗證失敗原因:")
            for idx, fail in enumerate(sample_failures):
                print(
                    f"  候選組 #{idx + 1} (group=0x{fail['group_addr']:X}, table=0x{fail['table_addr']:X}):"
                )
                print(f"    {fail['detail']}")
        print("============================\n")

    best_group, best_table, best_region, matched_level = pick_best_adaptive(
        handle, perfect, relaxed, minimal, layer_count
    )

    heuristics.record_success(best_group, best_region)

    pointers = []
    table_data = try_read(handle, best_table, layer_count * 8)
    if table_data and len(table_data) == layer_count * 8:
        pointers = list(struct.unpack(f"<{layer_count}Q", table_data))
    else:
        for i in range(layer_count):
            pointers.append(read_u64(handle, best_table + i * 8))

    return pointers


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

        header = lines[0].split("|")
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
            print(
                f"Layer cache no longer matches the active vinyl group ({valid}/{layer_count} valid); full scan needed."
            )
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
        shapes.append(
            {
                "type": int(raw.get("type", 0)),
                "data": [float(x) for x in raw.get("data", [])],
                "color": [int(c) for c in raw.get("color", [])],
            }
        )
    return shapes


def is_header_shape(s):
    return (
        s["type"] == 1
        and len(s["data"]) >= 4
        and abs(s["data"][0]) < 0.0001
        and abs(s["data"][1]) < 0.0001
        and len(s["color"]) >= 4
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

    write_bytes(handle, layer_ptr + LAYER_POS_OFFSET, struct.pack("<ff", x, -y))
    write_bytes(handle, layer_ptr + LAYER_SCALE_OFFSET, struct.pack("<ff", sx, sy))
    write_bytes(
        handle,
        layer_ptr + LAYER_ROTATION_OFFSET,
        struct.pack("<f", (360.0 - angle) % 360.0),
    )
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
        print(
            f"#{i + 1} shapeIndex={shape_index} ptr=0x{layer_pointers[i]:X} x={x:.3f} y(write)={-y:.3f} sx={sx:.3f} sy={sy:.3f}"
        )


def run_importer(
    json_path,
    layers=3000,
    dry_run=False,
    reverse=False,
    include_header=False,
    no_cache=False,
    scale_div=63.0,
    coord_scale=1.0,
    max_candidates=200000,
):
    print(
        f"Optimization Status: Numba acceleration = {'ENABLED' if HAS_NUMBA else 'DISABLED'}"
    )

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
        print(
            f"canvas={canvas_w:.3f}x{canvas_h:.3f} scaleDiv={scale_div:.3f} coordScale={coord_scale:.3f} order={'reverse' if reverse else 'table'} dryRun={dry_run}"
        )

        access_mask = (
            PROCESS_QUERY_INFORMATION
            | PROCESS_QUERY_LIMITED_INFORMATION
            | PROCESS_VM_READ
            | PROCESS_VM_WRITE
            | PROCESS_VM_OPERATION
        )
        handle = kernel32.OpenProcess(access_mask, False, pid)
        if not handle:
            raise OSError(f"OpenProcess failed. LastError={kernel32.GetLastError()}")

        try:
            cache_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "fh6-layer-table.cache"
            )
            layer_pointers = (
                None
                if no_cache
                else try_load_cached_layer_pointers(handle, cache_path, pid, layers)
            )

            if layer_pointers is None:
                layer_pointers = locate_layer_pointers(handle, layers, max_candidates)
                save_cached_layer_pointers(cache_path, pid, layers, layer_pointers)

            print(f"LiveryGroup found. Valid layer pointers={len(layer_pointers)}")

            n = min(len(shapes), len(layer_pointers))
            if dry_run:
                print_preview(
                    layer_pointers, shapes, canvas_w, canvas_h, options, min(n, 12)
                )
                print("Dry run only; no writes performed.")
                return 0

            written = 0
            for i in range(n):
                shape_index = len(shapes) - 1 - i if reverse else i
                layer_index = i
                layer_ptr = layer_pointers[layer_index]

                if score_layer(handle, layer_ptr) < 5:
                    continue

                write_shape(
                    handle, layer_ptr, shapes[shape_index], canvas_w, canvas_h, options
                )
                written += 1
                if written <= 12 or written % 100 == 0:
                    print(f"written {written}/{n} -> layerPtr=0x{layer_ptr:X}")

            print(f"DONE written={written}/{n}")
            if len(shapes) > len(layer_pointers):
                print(
                    "WARNING: JSON has more shapes than template layers. Remaining shapes were skipped."
                )

        finally:
            kernel32.CloseHandle(handle)

        return 0
    except Exception as ex:
        print(f"ERROR: {ex}", file=sys.stderr)
        return 1


# --- Main Entry ---
def main():
    parser = argparse.ArgumentParser(
        description="FH6 Import Layer Table Importer in Python"
    )
    parser.add_argument("json_path", help="Path to input geometry JSON file")
    parser.add_argument("--layers", type=int, default=3000, help="Template layer count")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and validate memory without writing",
    )
    parser.add_argument(
        "--reverse", action="store_true", help="Reverse shape order of drawing"
    )
    parser.add_argument(
        "--include-header",
        action="store_true",
        help="Include transparent header canvas shape",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore and bypass the layer address cache",
    )
    parser.add_argument(
        "--scale-div", type=float, default=63.0, help="Shape scale divisor"
    )
    parser.add_argument(
        "--coord-scale", type=float, default=1.0, help="Coordinate scale multiplier"
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=200000,
        help="Max candidates scanning threshold",
    )

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
        max_candidates=args.max_candidates,
    )


if __name__ == "__main__":
    sys.exit(main())
