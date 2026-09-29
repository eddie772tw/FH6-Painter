## 2025-02-12 - Numba Scanline Rendering Optimization
**Learning:** Naive bounding box rendering loops with pixel-by-pixel checks `if (rx*rx)*inv_rx2 + (ry*ry)*inv_ry2 <= 1.0` in Numba JIT functions are slow.
**Action:** Use an analytical scanline solver to calculate start/end x-coordinates per scanline using quadratic formula bounds based on sine/cosine projections. Precompute the division by hoisting `inv_a = np.float32(1.0 / a) if a > 0 else np.float32(0.0)` outside the loop to change expensive division into multiplication inside the hot loops. This provided a ~5x speedup for `draw_ellipse` and ~4.7x for `update_uncovered_mask`.

## 2026-05-28 - JIT Kernel Division Hoisting
**Learning:** In highly vectorized JIT kernels (Numba and Taichi), replacing inner-loop division operations with multiplication by a precomputed inverse provides a significant and measurable performance boost without breaking vectorization. Specifically, replacing `/ count` with `* inv_count` and `/ 3.0` with `* 0.3333333333333333` in accumulation and error estimation passes yielded up to a 15% reduction in kernel execution time according to local benchmarks.
**Action:** Always scrutinize inner loops in computationally intensive JIT functions for division operations. Hoist the division by calculating the reciprocal outside the loop and multiplying inside the loop.

## 2026-05-29 - Taichi GPU Scanline Rendering Optimization
**Learning:** Naive bounding box rendering loops with pixel-by-pixel checks `if (rx*rx)*inv_rx2 + (ry*ry)*inv_ry2 <= 1.0` in Taichi GPU JIT functions (`draw_ellipse_gpu` and `update_uncovered_mask_gpu`) are slow and cause thread divergence inside inner loops on the GPU.
**Action:** Use an analytical scanline solver (quadratic roots based on sine/cosine projections) to calculate start/end x-coordinates per scanline. Precompute divisions by hoisting `inv_a = 1.0 / a if a > 0.0 else 0.0` outside the loop to change expensive division into multiplication inside the hot loops. This matches the optimization strategy used in Numba CPU kernels and significantly speeds up Taichi execution on the GPU by avoiding thread divergence.

## 2026-06-02 - Division Hoisting: alpha / 255.0
**Learning:** I found multiple instances where `alpha / 255.0` and `step / optimization_steps` were being computed repeatedly inside of loops in `evaluators/numba_kernels.py` and `evaluators/taichi_evaluator.py`. Since divisions are slow, especially in inner loops, replacing division by multiplication using precalculated constants (`alpha * 0.00392156862745098` and `step * inv_opt_steps`) can yield a performance improvement.
**Action:** Replaced division operations with equivalent multiplication using hoisted reciprocal values or pre-calculated constants across evaluator kernels.

## 2026-06-03 - Loop Unswitching in JIT Kernels
**Learning:** In highly intensive accumulation loops (like those evaluating thousands of ellipse candidates), runtime boolean flags (e.g., `use_weight`, `use_uncovered`) inside the inner loops prevent compilers (LLVM/Taichi) from fully vectorizing and unswitching the loops automatically due to complexity thresholds. This results in millions of redundant branch evaluations and multiplications by 1.0 (or its typecast equivalent).
**Action:** Apply manual loop unswitching by branching on these boolean flags outside the main pixel-processing `y`/`x` loops. Create a dedicated "fast path" loop for the default configuration that completely omits weight computation and multiplications, significantly boosting throughput.

## 2026-06-04 - Scanline Discriminant Simplification
**Learning:** The equation `b_quad * b_quad - a * c_val` inside the ellipse scanline discriminant loop simplifies to `a - dy * dy * inv_rx2 * inv_ry2`. The previous form required calculating `c_y_coeff` and then computing `c_val = dy * dy * c_y_coeff - 1.0` and `discriminant = b_quad * b_quad - a * c_val` in the innermost loop (4 multiplies, 2 subtracts). The new formula requires just `a - dy * dy * inv_rx2_ry2` (2 multiplies, 1 subtract). This mathematical simplification removes instructions from the tightest inner loop, accelerating pixel coverage determination without affecting results.
**Action:** Look for algebraic simplifications in heavily called mathematical loops (like geometry boundary solvers). Expanding and factoring intermediate terms can often reveal a simpler, more computationally efficient equivalent.

## 2026-06-05 - Array Shape Check Hoisting
**Learning:** In highly intensive per-pixel accumulation loops (like those drawing millions of ellipses), executing `canvas.shape[2] == 4` inside the innermost loop forces the JIT compiler to repeatedly evaluate a conditional branch and perform a redundant dimension lookup. Compilers (like LLVM via Numba) often fail to automatically unswitch these bounds checks if they involve structural lookups.
**Action:** Manually unswitch the loop by hoisting constant shape evaluations `has_alpha = canvas.shape[2] == 4` outside the spatial Y/X loops and create dedicated loop structures for the RGBA and RGB paths. This significantly enhances branch predictability and vectorization for performance-critical kernels.

## 2026-07-02 - Forward Differencing & Array Slicing in Numba CPU Evaluator
**Learning:** Expanding `(y - y_c)^2` inside the tight `for y` loops using standard quadratic discriminant `a - dy^2 * inv_rx2` creates a heavy multiplication load per row. In addition, nested Python loops in Numba for contiguous horizontal 1D array operations (like filling an `uncovered_map` row) compile worse than native slice assignments (`uncovered_map[y, x_start:x_end+1] = 1.0`). However, Numba degrades performance when 3D slice assignment is attempted (like `canvas[y, x_start:x_end+1, c] = ...`), rendering standard looping faster.
**Action:** Replace `dy^2` mathematical bound checks iteratively with forward differencing (`discriminant += disc_step_1 + disc_step_2`) to remove the multiplication step inside bounds evaluations. Always use slice assignments for simple 2D fills in Numba, but retain loops for 3D or conditional assignments.

## 2024-05-26 - [Numba Loop Unswitching with Constant Flags]
**Learning:** In Numba JIT kernels, unswitching a loop based on `check_contour` in the innermost loop (moving the `if check_contour:` check OUTSIDE the `for x in range(...)` loop) yields huge performance improvements (nearly 10x speedup in CPU Multithreading mode) because it removes branching for every pixel evaluated.
**Action:** When working with Numba JIT kernels, proactively look for static/configuration boolean flags inside innermost tight loops and unswitch them (hoist them outside) even if it means duplicating the loop body, as the Numba compiler struggles to optimize this automatically.

## 2026-07-06 - Numba 3D Slice Assignment Regressions
**Learning:** In Numba JIT kernels, attempting to do 3D slice assignments like `canvas[:, :, 0] = r_val` fails to vectorize effectively and executes substantially slower than explicitly writing out the nested 2D loops `for y in range(height): for x in range(width): canvas[y, x, 0] = r_val`. This causes measurable performance regressions (e.g., ~3x slowdown for `rebuild_canvas_jit`).
**Action:** When filling or rebuilding large multi-dimensional arrays (like a 3D canvas) in Numba, avoid using 3D slice syntax and prefer explicitly looping through the dimensions and performing point assignments.

## 2026-07-15 - Numba 2D Boolean Mask Assignment
**Learning:** In Numba JIT functions compiled in `nopython` mode, 2D boolean mask assignments (e.g., `arr[mask > threshold] = value`) fail to compile due to typing errors with setitem (`Multi-dimensional indices are not supported.`). While Numba supports 1D boolean masks, it cannot natively vectorize this pattern across multi-dimensional arrays without throwing `NumbaTypeError`.
**Action:** When performing conditional updates against a multi-dimensional threshold map inside Numba JIT kernels (like `alpha_mask > 10.0`), use explicit nested 2D spatial loops to iterate over coordinates instead of boolean mask assignment arrays to prevent compilation failures.

## 2026-07-20 - Loop unswitching in Taichi Evaluator for validation check
**Learning:** The `check_contour` and `use_freeze` configuration flags in the inner `evaluate_candidate_ti` loop inside `taichi_evaluator.py` caused branching for every pixel checked. This prevented the LLVM/Taichi compiler from optimally executing the tight loop. Numba CPU already implemented unswitching for `use_freeze` externally, and `taichi_evaluator.py` was lagging in this optimization.
**Action:** Unswitched the `check_contour` and `use_freeze` validations in the Taichi loop by hoisting these boolean checks outside of the pixel Y/X evaluation loops.

## 2026-07-20 - Taichi GPU Loop Unswitching for Boolean Flags
**Learning:** In the highly executed Taichi scanline evaluation kernel (`evaluate_candidate_ti`), configuration flags such as `check_contour` and `use_freeze` (in the validation pass) and `use_weight`/`use_uncovered` (in the accumulation pass) were checked inside the inner loops. This per-pixel branching causes thread divergence and inhibits Taichi/LLVM from adequately vectorizing or unswitching the loops automatically on the GPU. Numba kernels previously incorporated unswitching for `use_freeze` and others, but Taichi was lagging.
**Action:** Unswitched these configuration checks by manually hoisting the `if` branches completely outside the spatial bounding box iteration loops, creating discrete code paths (fast/slow branches) for the inner core. While this duplicates loop structures in source code, it dramatically lowers branch overhead during runtime execution.

## 2026-07-21 - Forward Differencing & Loop-Carry Dependency in Taichi GPU Kernels
**Learning:** While forward differencing works perfectly in sequential loops (like the `while` loops inside the JIT helper `evaluate_candidate_ti`), it is fundamentally incompatible with outermost `for` loops in `@ti.kernel` (like `draw_ellipse_gpu` and `update_uncovered_mask_gpu`). Since Taichi automatically parallelizes outermost kernel `for` loops across GPU threads, introducing variables modified inside the loop that are defined outside (like `discriminant` and `b_quad`) converts them into reduction variables. Because reading reduction variables inside a parallel loop is undefined behavior on GPU backends, threads read stale/initial values, corrupting the canvas.
**Action:** Limit forward differencing optimization strictly to sequential functions (`evaluate_candidate_ti`). Revert parallel kernels (`draw_ellipse_gpu` and `update_uncovered_mask_gpu`) to use parallel-safe coordinate calculations (`dy = y - y_c`, etc.) to preserve correctness.
## 2024-05-18 - [Optimize Synchronous File I/O in WebSocket Handlers]
**Learning:** Performing synchronous file I/O operations directly inside an `async def` function (like a WebSocket message handler) blocks the main asyncio event loop, causing server unresponsiveness and high latencies. While `json.load` releases the GIL when reading from disk, the subsequent allocation of Python dictionaries and lists reacquires the GIL, resulting in minor GIL contention even when offloaded to a `ThreadPoolExecutor`.
**Action:** Use `asyncio.get_running_loop().run_in_executor(None, func)` to offload all blocking synchronous I/O or CPU-bound code from the main event loop. For loading many files, use `asyncio.gather` with executor tasks to fully leverage disk concurrency and avoid hanging WebSocket connections.
