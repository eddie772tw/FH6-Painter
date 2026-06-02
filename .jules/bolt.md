## 2025-02-12 - Numba Scanline Rendering Optimization
**Learning:** Naive bounding box rendering loops with pixel-by-pixel checks `if (rx*rx)*inv_rx2 + (ry*ry)*inv_ry2 <= 1.0` in Numba JIT functions are slow.
**Action:** Use an analytical scanline solver to calculate start/end x-coordinates per scanline using quadratic formula bounds based on sine/cosine projections. Precompute the division by hoisting `inv_a = np.float32(1.0 / a) if a > 0 else np.float32(0.0)` outside the loop to change expensive division into multiplication inside the hot loops. This provided a ~5x speedup for `draw_ellipse` and ~4.7x for `update_uncovered_mask`.

## 2026-05-28 - JIT Kernel Division Hoisting
**Learning:** In highly vectorized JIT kernels (Numba and Taichi), replacing inner-loop division operations with multiplication by a precomputed inverse provides a significant and measurable performance boost without breaking vectorization. Specifically, replacing `/ count` with `* inv_count` and `/ 3.0` with `* 0.3333333333333333` in accumulation and error estimation passes yielded up to a 15% reduction in kernel execution time according to local benchmarks.
**Action:** Always scrutinize inner loops in computationally intensive JIT functions for division operations. Hoist the division by calculating the reciprocal outside the loop and multiplying inside the loop.

## 2026-05-29 - Taichi GPU Scanline Rendering Optimization
**Learning:** Naive bounding box rendering loops with pixel-by-pixel checks `if (rx*rx)*inv_rx2 + (ry*ry)*inv_ry2 <= 1.0` in Taichi GPU JIT functions (`draw_ellipse_gpu` and `update_uncovered_mask_gpu`) are slow and cause thread divergence inside inner loops on the GPU.
**Action:** Use an analytical scanline solver (quadratic roots based on sine/cosine projections) to calculate start/end x-coordinates per scanline. Precompute divisions by hoisting `inv_a = 1.0 / a if a > 0.0 else 0.0` outside the loop to change expensive division into multiplication inside the hot loops. This matches the optimization strategy used in Numba CPU kernels and significantly speeds up Taichi execution on the GPU by avoiding thread divergence.

## 2026-06-01 - Pure Python Scanline Rendering Optimization
**Learning:** The analytical scanline solver (quadratic roots based on sine/cosine projections) previously used in Numba and Taichi JIT kernels also significantly boosts performance in Pure Python environments without explicit vectorization. It eliminates conditional branching inside tight inner loops, which is inherently slow in CPython due to evaluation overhead.
**Action:** Apply the analytical scanline solver to purely Python bounding box iteration loops where mathematical solutions are faster than procedural pixel-by-pixel boundary checking, reducing evaluation time during fallback operations.
## 2026-06-02 - Division Hoisting: alpha / 255.0
**Learning:** I found multiple instances where `alpha / 255.0` and `step / optimization_steps` were being computed repeatedly inside of loops in `evaluators/pure_python_evaluator.py`, `evaluators/numba_kernels.py`, and `evaluators/taichi_evaluator.py`. Since divisions are slow, especially in inner loops, replacing division by multiplication using precalculated constants (`alpha * 0.00392156862745098` and `step * inv_opt_steps`) can yield a performance improvement.
**Action:** Replaced division operations with equivalent multiplication using hoisted reciprocal values or pre-calculated constants across evaluator kernels.
