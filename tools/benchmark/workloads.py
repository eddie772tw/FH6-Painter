#!/usr/bin/env python3
"""程式化測試圖庫 — 以 NumPy 實時生成決定性標準測試圖。"""
import numpy as np


def generate_geometric(w, h):
    """生成高對比幾何圖形（測試大面積覆蓋與記憶體頻寬）。"""
    img = np.zeros((h, w, 3), dtype=np.float32)
    # 中間白矩形
    cy, cx = h // 2, w // 2
    img[cy - h//4 : cy + h//4, cx - w//4 : cx + w//4, :] = 255.0
    # 左上紅圓
    Y, X = np.ogrid[:h, :w]
    dist_r = np.sqrt((X - w//4)**2 + (Y - h//4)**2)
    img[dist_r <= min(w, h)//6, 0] = 255.0
    img[dist_r <= min(w, h)//6, 1:3] = 0.0
    # 右下藍圓
    dist_b = np.sqrt((X - 3*w//4)**2 + (Y - 3*h//4)**2)
    img[dist_b <= min(w, h)//8, 2] = 255.0
    img[dist_b <= min(w, h)//8, 0:2] = 0.0
    return img, None


def generate_gradient(w, h):
    """生成平滑漸層（測試 Alpha 混合與浮點運算 ALU 壓力）。"""
    Y, X = np.meshgrid(np.linspace(0, 255, h), np.linspace(0, 255, w), indexing='ij')
    img = np.zeros((h, w, 3), dtype=np.float32)
    img[:, :, 0] = Y  # R通道 Y漸層
    img[:, :, 1] = X  # G通道 X漸層
    img[:, :, 2] = 255.0 - Y  # B通道 反向Y漸層
    return img, None


def generate_high_frequency(w, h):
    """生成高頻正弦波紋理（測試微小形狀搜尋、分支預測與 Cache 命中率）。"""
    y_coords = np.linspace(0, 2 * np.pi * 15, h)
    x_coords = np.linspace(0, 2 * np.pi * 15, w)
    X, Y = np.meshgrid(x_coords, y_coords)
    val = (np.sin(X) * np.cos(Y) + 1.0) * 127.5
    img = np.zeros((h, w, 3), dtype=np.float32)
    img[:, :, 0] = val
    img[:, :, 1] = val
    img[:, :, 2] = val
    return img, None


def generate_alpha_mask(w, h):
    """生成帶有複雜 Alpha 透明背景的圖形（測試 check_contour 邊界剔除邏輯）。"""
    img, _ = generate_gradient(w, h)
    Y, X = np.ogrid[:h, :w]
    center_y, center_x = h / 2.0, w / 2.0
    dist = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
    angle = np.arctan2(Y - center_y, X - center_x)
    r_limit = (min(w, h) * 0.45) * (1.0 + 0.25 * np.sin(5 * angle))
    alpha_mask = np.clip((r_limit - dist) / 15.0, 0.0, 1.0) * 255.0
    return img, alpha_mask


# 標準測試圖清單
WORKLOADS = [
    {"name": "Geometric", "generator": generate_geometric},
    {"name": "Gradient", "generator": generate_gradient},
    {"name": "High_Frequency", "generator": generate_high_frequency},
    {"name": "Alpha_Mask", "generator": generate_alpha_mask},
]
