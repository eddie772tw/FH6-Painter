#!/usr/bin/env python3
from abc import ABC, abstractmethod

import numpy as np


class BaseEvaluator(ABC):
    def __init__(self, target_image: np.ndarray, alpha_mask: np.ndarray = None):
        """初始化評估器。
        GPU 運算核心外掛應在此處將目標圖片和 alpha 遮罩上載至 VRAM 常駐。

        :param target_image: 目標影像矩陣 (H, W, 3) - float32
        :param alpha_mask: 目標影像的 alpha 遮罩 (H, W) - float32
        """
        self.target_image = target_image
        self.alpha_mask = (
            alpha_mask if alpha_mask is not None else np.zeros((1, 1), dtype=np.float32)
        )

        # 靜態影像平面通道拆分，以支援 CPU 與 GPU 的向量化連續載入
        self.target_r = np.ascontiguousarray(target_image[:, :, 0])
        self.target_g = np.ascontiguousarray(target_image[:, :, 1])
        self.target_b = np.ascontiguousarray(target_image[:, :, 2])

    @abstractmethod
    def get_name(self) -> str:
        """回傳評估器的名稱，例如 'Numba JIT (CPU Multithreading)'"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """回傳此評估器所需的硬體或依賴庫是否可用"""
        pass

    @abstractmethod
    def get_device_type(self) -> str:
        """回傳計算裝置種類，例如 'CPU' 或 'GPU'"""
        pass

    @abstractmethod
    def search_best_shape(
        self, current_canvas: np.ndarray, batch_size: int, params: dict
    ) -> tuple:
        """執行批次搜尋與優化，尋找最佳擬合橢圓形狀與其對應的最低誤差。
        本方法應完全由底層加速核心平行執行，避免來回傳輸 VRAM。

        :param current_canvas: 當前畫布圖像 (H, W, 3) - float32
        :param batch_size: 隨機產生的候選形狀數量
        :param params: 包含各種優化控制參數的字典，例如：
                       - 'optimization_steps': 爬山/退火優化步數
                       - 'check_contour': 是否限制在 alpha 輪廓內
                       - 'use_importance': 是否啟用重點採樣
                       - 'error_prob': 誤差機率分佈圖 (H, W) - float32
                       - 'sa_enabled': 是否啟用模擬退火
                       - 'sa_initial_temp': 模擬退火初溫
                       - 'sa_cooling_rate': 模擬退火冷卻率
                       - 'current_max_r': 形狀最大半徑限制
                       - 'use_freeze': 是否啟用凍結遮罩
                       - 'freeze_mask': 凍結遮罩矩陣 (H, W) - uint8
                       - 'use_weight': 是否啟用誤差加權
                       - 'weight_map': 誤差加權矩陣 (H, W) - float32
                       - 'use_uncovered': 是否啟用未覆蓋區域優先加權
                       - 'uncovered_map': 未覆蓋優先度地圖 (H, W) - float32
        :return: 回傳元組 (best_shape, min_error)，其中：
                 - best_shape: [x_c, y_c, r_x, r_y, theta_deg, r, g, b, alpha]
                 - min_error: 該形狀產生的 Delta MSE 誤差值
        """
        pass

    @abstractmethod
    def draw_shape_on_canvas(
        self,
        canvas: np.ndarray,
        x_c: float,
        y_c: float,
        r_x: float,
        r_y: float,
        theta_rad: float,
        r: float,
        g: float,
        b: float,
        alpha: float,
    ) -> None:
        """在畫布上渲染繪製一個形狀（JIT/硬體加速）。

        :param canvas: 待更新的畫布圖像 (H, W, 3)
        """
        pass

    @abstractmethod
    def rebuild_canvas(
        self,
        canvas: np.ndarray,
        shapes_list: list,
        avg_r: float,
        avg_g: float,
        avg_b: float,
    ) -> None:
        """根據貼圖形狀清單，重新繪製並重建整個畫布圖像（JIT/硬體加速）。

        :param canvas: 目標畫布圖像
        :param shapes_list: 車貼形狀清單（包含背景 header 和各層橢圓形狀）
        :param avg_r, avg_g, avg_b: 背景平均色彩
        """
        pass

    @abstractmethod
    def run_redundancy_check(
        self, shapes_list: list, width: int, height: int, final_check: bool = False
    ) -> list:
        """透過反向遮擋追蹤演算法，篩選並排除已被完全覆蓋/遮蔽的冗餘貼圖形狀（JIT/硬體加速）。

        :param shapes_list: 原始貼圖形狀清單
        :param width: 畫布寬度
        :param height: 畫布高度
        :param final_check: 是否為末尾專用檢查（不刪除，改重置為畫布外微型 shape）
        :return: 優化過後的貼圖形狀清單
        """
        pass

    @abstractmethod
    def init_uncovered_map(
        self, width: int, height: int, has_alpha: bool, bias: float
    ) -> np.ndarray:
        """初始化未覆蓋優先度地圖。

        :return: (H, W) 的優先度權重矩陣
        """
        pass

    @abstractmethod
    def update_uncovered_mask(
        self,
        uncovered_map: np.ndarray,
        x_c: float,
        y_c: float,
        r_x: float,
        r_y: float,
        theta_rad: float,
    ) -> None:
        """當繪製新形狀時，在未覆蓋優先度地圖中重置被覆蓋的區域權重。
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """釋放運算引擎佔用的資源與 GPU 記憶體"""
        pass
