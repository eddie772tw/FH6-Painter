# Forza Painter - Advanced Python Engine

> The Ultimate High-Performance Vectorization & Shape Generation Engine for Forza Horizon.

This project is a modernized, pure-Python architecture overhaul of the original `forza-painter` (C++). It replaces the legacy standard geometric solver with two ultra-high-performance parallel computing backends, unlocking real-time generation speeds and infinite scalability while outputting 100% valid layer injection files for Forza Horizon games.

## 🚀 Key Features

* **Python Numba JIT Engine (Option 3)**:
  * Utilizes LLVM to compile pure Python down to raw x86-64 machine code.
  * Bypasses the Python Global Interpreter Lock (GIL) completely using OpenMP multi-threading.
  * **Algorithmic Optimizations**: Bounding-Box scanline limiting and "Active Redundancy Shedding" (periodically scans the mathematical visibility map to remove fully occluded shapes on-the-fly, recovering layer slots for finer details).
  * Evaluates thousands of physical shape candidates per second!
* **PyTorch GPU / DirectML Engine (Option 2)**:
  * Leverages `torch` and `torch-directml` for full tensor-based vector calculations.
  * Massively parallel grid evaluation running entirely on the GPU (DirectX 12 / CUDA compatible).
* **Real-time OpenCV Rendering**:
  * Live-streaming preview window of the canvas evolution.
  * **Graceful Abort**: Press `Q`, `ESC`, or click the `[X]` on the preview window to prematurely stop generation and safely export the current progress!

## 🛠️ Installation & Setup

1. **Install Python 3.12+**
2. **Create a Virtual Environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
3. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

## 🎮 Usage

Simply **drag and drop an image** (e.g. `test.png`) directly onto the **`python_painter_launcher.bat`** file!

Or run it via command line:
```powershell
.\.venv\Scripts\python.exe python_painter\main.py "path\to\image.png"
```

You will be greeted with the engine selection menu:
```text
============================================================
Select Generator Engine:
  [1] Native C++ Generator (used in forza-painter and Geometrize-lib)
  [2] GPU Accelerated Generator (Support both NVIDIA CUDA and AMD ROCm)
  [3] Python Numba JIT Generator (Fastest in most rigs)
============================================================
```

## ⚖️ License & Attribution
This project is licensed under the **MIT License**.

- Python Optimization & Architecture Overhaul: (c) 2026 eddie772tw
- Based on the original `forza-painter`: Copyright (c) 2021 AE (A-Dawg#0001)
- Geometrize-lib logic: Copyright (c) 2021 Sam Twidale
- Primitive library: Copyright (c) 2016 Michael Fogleman
