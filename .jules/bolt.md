## $(date +%Y-%m-%d) - Algebraic Scanline Optimization
**Learning:** Found a severe CPU bottleneck in Numba kernels iterating over a full 2D bounding box and conditionally checking shape coverage inside the tightest inner loop. Mathematical boundary solving avoids inner-loop conditionals but can introduce division-by-zero crashes on degenerate shapes if not carefully guarded.
**Action:** When migrating from 2D bounding box tests to 1D algebraic scanline solvers in JIT kernels, always include mathematical safety guards (like `a > 0.0`) to handle degenerate input parameters gracefully.
