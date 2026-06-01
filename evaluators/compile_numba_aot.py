#!/usr/bin/env python3
import os
import sys
from numba.pycc import CC
from numba import float32, float64, int32, boolean, uint8, types

# 建立 AOT 編譯模組物件
cc = CC('numba_kernels_aot')
cc.verbose = True

# 1. evaluate_candidate 導出配置
evaluate_candidate_sig = types.Tuple((float32, float32, float32, float32))(
    float32[:, :],  # target_r
    float32[:, :],  # target_g
    float32[:, :],  # target_b
    float32[:, :],  # canvas_r
    float32[:, :],  # canvas_g
    float32[:, :],  # canvas_b
    float32,        # x_c
    float32,        # y_c
    float32,        # r_x
    float32,        # r_y
    float32,        # theta
    int32,          # alpha
    float32[:, :],  # alpha_mask
    boolean,        # check_contour
    boolean,        # use_freeze
    uint8[:, :],    # freeze_mask
    boolean,        # use_weight
    float32[:, :],  # weight_map
    boolean,        # use_uncovered
    float32[:, :]   # uncovered_map
)
cc.export('evaluate_candidate', evaluate_candidate_sig)(
    # 直接在腳本載入時從 numba_kernels 獲取底層函數
    sys.modules.setdefault('evaluators.numba_kernels', None) or __import__('numba_kernels').evaluate_candidate
)

# 2. draw_ellipse 導出配置
draw_ellipse_sig = types.void(
    float32[:, :, :],  # canvas
    float32,           # x_c
    float32,           # y_c
    float32,           # r_x
    float32,           # r_y
    float32,           # theta
    float32,           # r
    float32,           # g
    float32,           # b
    float32            # alpha
)
cc.export('draw_ellipse', draw_ellipse_sig)(
    __import__('numba_kernels').draw_ellipse
)

# 3. init_uncovered_map 導出配置
init_uncovered_map_sig = float32[:, :](
    int32,          # width
    int32,          # height
    boolean,        # has_alpha
    float32[:, :],  # alpha_mask
    float32         # bias
)
cc.export('init_uncovered_map', init_uncovered_map_sig)(
    __import__('numba_kernels').init_uncovered_map
)

# 4. update_uncovered_mask 導出配置
update_uncovered_mask_sig = types.void(
    float32[:, :],  # uncovered_map
    float32,        # x_c
    float32,        # y_c
    float32,        # r_x
    float32,        # r_y
    float32         # theta
)
cc.export('update_uncovered_mask', update_uncovered_mask_sig)(
    __import__('numba_kernels').update_uncovered_mask
)

# 5. parallel_random_search 導出配置
parallel_random_search_sig = types.Tuple((float32, float32, float32, float32, float32, int32, float32, float32, float32, float32))(
    float32[:, :],  # target_r
    float32[:, :],  # target_g
    float32[:, :],  # target_b
    float32[:, :],  # canvas_r
    float32[:, :],  # canvas_g
    float32[:, :],  # canvas_b
    int32,          # num_candidates
    int32,          # width
    int32,          # height
    float32,        # max_r
    float32[:, :],  # alpha_mask
    boolean,        # check_contour
    boolean,        # use_importance
    float32[:, :],  # error_prob
    boolean,        # use_freeze
    uint8[:, :],    # freeze_mask
    boolean,        # use_weight
    float32[:, :],  # weight_map
    boolean,        # use_uncovered
    float32[:, :]   # uncovered_map
)
cc.export('parallel_random_search', parallel_random_search_sig)(
    __import__('numba_kernels').parallel_random_search
)

# 6. serial_hill_climb 導出配置
serial_hill_climb_sig = types.Tuple((float64, float64, float64, float64, float64, int32, int32, int32, int32, float64))(
    float32[:, :],  # target_r
    float32[:, :],  # target_g
    float32[:, :],  # target_b
    float32[:, :],  # canvas_r
    float32[:, :],  # canvas_g
    float32[:, :],  # canvas_b
    float32,        # x_c
    float32,        # y_c
    float32,        # r_x
    float32,        # r_y
    float32,        # theta
    int32,          # alpha
    float32,        # r
    float32,        # g
    float32,        # b
    float32,        # best_delta
    int32,          # optimization_steps
    float32[:, :],  # alpha_mask
    boolean,        # check_contour
    boolean,        # sa_enabled
    float32,        # initial_temp
    float32,        # cooling_rate
    float32,        # max_r
    boolean,        # use_freeze
    uint8[:, :],    # freeze_mask
    boolean,        # use_weight
    float32[:, :],  # weight_map
    boolean,        # use_uncovered
    float32[:, :]   # uncovered_map
)
cc.export('serial_hill_climb', serial_hill_climb_sig)(
    __import__('numba_kernels').serial_hill_climb
)

# 7. run_redundancy_check_jit 導出配置
run_redundancy_check_sig = boolean[:](
    float32[:, :],  # shapes_data
    int32[:, :],    # shapes_color
    int32[:],       # shapes_type
    int32,          # width
    int32           # height
)
cc.export('run_redundancy_check_jit', run_redundancy_check_sig)(
    __import__('numba_kernels').run_redundancy_check_jit
)

# 8. rebuild_canvas_jit 導出配置
rebuild_canvas_sig = types.void(
    float32[:, :, :],  # canvas
    float32,           # avg_r
    float32,           # avg_g
    float32,           # avg_b
    float32,           # avg_a
    float32[:, :],     # shapes_data
    int32[:, :]        # shapes_color
)
cc.export('rebuild_canvas_jit', rebuild_canvas_sig)(
    __import__('numba_kernels').rebuild_canvas_jit
)


if __name__ == "__main__":
    cc.compile()
