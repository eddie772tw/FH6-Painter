#!/usr/bin/env python3
import os
import sys

# 阻斷隱式 Vulkan Layers（如 Game Capture, OBS, Discord overlay 等）注入，防止產生大量垃圾調試輸出並提升啟動穩定度
os.environ["VK_LOADER_LAYERS_DISABLE"] = "~implicit~"
os.environ["DISABLE_OBS_CAPTURE"] = "1"

# Ensure we can import from the tools directory
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))

from gui.app import ForzaStudioGUI, main

if __name__ == "__main__":
    main()
