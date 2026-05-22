## 2024-06-12 - Mathematical Optimizations Beat Raw Iteration
**Learning:** Even when using Numba JIT, raw bounding box scanning for rasterization involves high overhead because of branch mispredictions inside hot loops. Solving the math beforehand (e.g. roots of the quadratic equation for a rotated ellipse) to find exact row bounds can reduce execution time by nearly 50% compared to brute-forcing the inequality on every pixel.
**Action:** When optimizing Numba code, look for opportunities to replace nested loops and conditionals with precomputed mathematical bounds.
