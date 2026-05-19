import os
import sys
import time
import math
import json
from typing import Dict, Any, List, Tuple
from PIL import Image
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.dirname(current_dir))
import torch
import torch_directml

class GPUImageGenerator:

    def __init__(self, device_name: str, random_samples: int, mutated_samples: int):
        if device_name == 'directml':
            self.device = torch_directml.device()
        else:
            self.device = torch.device(device_name)
        self.random_samples = random_samples
        self.mutated_samples = mutated_samples
        self.max_batch_size = 500
        y_g, x_g = torch.meshgrid(torch.linspace(-1.0, 1.0, 256, device=self.device), torch.linspace(-1.0, 1.0, 256, device=self.device), indexing='ij')
        self.x_grid = x_g.unsqueeze(0)
        self.y_grid = y_g.unsqueeze(0)

    def optimize_image(self, img_path: str, target_layers: int, output_json: str) -> bool:
        print('\n' + '=' * 80)
        print('          FORZA PAINTER HIGH-PERFORMANCE GPU SOLVER ACTIVE')
        print('=' * 80)
        print(f'Loading Target Image: {img_path}')
        try:
            pil_img = Image.open(img_path).convert('RGB')
        except Exception as e:
            print(f'[Error] Failed to read target image: {e}')
            return False
        pil_img_resized = pil_img.resize((256, 256), Image.Resampling.LANCZOS)
        target = torch.from_numpy(import_numpy_array_data_helper(pil_img_resized)).permute(2, 0, 1).float().to(self.device) / 255.0
        mean_color = target.mean(dim=[1, 2], keepdim=True)
        canvas = mean_color.clone().repeat(1, 256, 256)
        shapes_json = []
        bg_r = int(mean_color[0, 0, 0].item() * 255.0)
        bg_g = int(mean_color[1, 0, 0].item() * 255.0)
        bg_b = int(mean_color[2, 0, 0].item() * 255.0)
        shapes_json.append({'type': 1, 'data': [0.0, 0.0, 3000.0, 3000.0], 'color': [bg_r, bg_g, bg_b, 0]})
        print(f'Target layers to solve: {target_layers} ellipses')
        print(f'Optimization pipeline: {self.random_samples} random / {self.mutated_samples} mutations per shape')
        print('Solving...')
        start_time = time.perf_counter()

        def solve_optimal_colors(masks_tensor: torch.Tensor) -> torch.Tensor:
            mask_sums = masks_tensor.sum(dim=[1, 2], keepdim=True) + 1e-06
            target_weighted = (target.unsqueeze(0) * masks_tensor.unsqueeze(1)).sum(dim=[2, 3], keepdim=True)
            return target_weighted / mask_sums.unsqueeze(1)
        with torch.no_grad():
            for layer in range(target_layers):
                best_loss = 1000000000.0
                best_cx = 0.0
                best_cy = 0.0
                best_rx = 0.1
                best_ry = 0.1
                best_theta = 0.0
                best_color = torch.tensor([1.0, 1.0, 1.0], device=self.device)
                remaining = self.random_samples
                while remaining > 0:
                    batch_size = min(remaining, self.max_batch_size)
                    remaining -= batch_size
                    cx = torch.rand(batch_size, 1, 1, device=self.device) * 2.0 - 1.0
                    cy = torch.rand(batch_size, 1, 1, device=self.device) * 2.0 - 1.0
                    rx = torch.rand(batch_size, 1, 1, device=self.device) * 0.4 + 0.005
                    ry = torch.rand(batch_size, 1, 1, device=self.device) * 0.4 + 0.005
                    theta = torch.rand(batch_size, 1, 1, device=self.device) * 2.0 * math.pi
                    cos_t = torch.cos(theta)
                    sin_t = torch.sin(theta)
                    dx = self.x_grid - cx
                    dy = self.y_grid - cy
                    x_p = dx * cos_t + dy * sin_t
                    y_p = -dx * sin_t + dy * cos_t
                    masks = ((x_p / rx) ** 2 + (y_p / ry) ** 2 <= 1.0).float()
                    opt_colors = solve_optimal_colors(masks)
                    rendered = canvas.unsqueeze(0) * (1.0 - masks.unsqueeze(1)) + opt_colors * masks.unsqueeze(1)
                    losses = torch.mean((rendered - target.unsqueeze(0)) ** 2, dim=[1, 2, 3])
                    min_idx = torch.argmin(losses).item()
                    min_loss = losses[min_idx].item()
                    if min_loss < best_loss:
                        best_loss = min_loss
                        best_cx = cx[min_idx, 0, 0].item()
                        best_cy = cy[min_idx, 0, 0].item()
                        best_rx = rx[min_idx, 0, 0].item()
                        best_ry = ry[min_idx, 0, 0].item()
                        best_theta = theta[min_idx, 0, 0].item()
                        best_color = opt_colors[min_idx].squeeze(-1).squeeze(-1)
                remaining = self.mutated_samples
                mutate_rate = 0.08
                while remaining > 0:
                    batch_size = min(remaining, self.max_batch_size)
                    remaining -= batch_size
                    cx = best_cx + torch.randn(batch_size, 1, 1, device=self.device) * mutate_rate
                    cy = best_cy + torch.randn(batch_size, 1, 1, device=self.device) * mutate_rate
                    rx = best_rx + torch.randn(batch_size, 1, 1, device=self.device) * mutate_rate
                    ry = best_ry + torch.randn(batch_size, 1, 1, device=self.device) * mutate_rate
                    theta = best_theta + torch.randn(batch_size, 1, 1, device=self.device) * mutate_rate
                    cx = torch.clamp(cx, -1.0, 1.0)
                    cy = torch.clamp(cy, -1.0, 1.0)
                    rx = torch.clamp(rx, 0.001, 1.0)
                    ry = torch.clamp(ry, 0.001, 1.0)
                    cos_t = torch.cos(theta)
                    sin_t = torch.sin(theta)
                    dx = self.x_grid - cx
                    dy = self.y_grid - cy
                    x_p = dx * cos_t + dy * sin_t
                    y_p = -dx * sin_t + dy * cos_t
                    masks = ((x_p / rx) ** 2 + (y_p / ry) ** 2 <= 1.0).float()
                    opt_colors = solve_optimal_colors(masks)
                    rendered = canvas.unsqueeze(0) * (1.0 - masks.unsqueeze(1)) + opt_colors * masks.unsqueeze(1)
                    losses = torch.mean((rendered - target.unsqueeze(0)) ** 2, dim=[1, 2, 3])
                    min_idx = torch.argmin(losses).item()
                    min_loss = losses[min_idx].item()
                    if min_loss < best_loss:
                        best_loss = min_loss
                        best_cx = cx[min_idx, 0, 0].item()
                        best_cy = cy[min_idx, 0, 0].item()
                        best_rx = rx[min_idx, 0, 0].item()
                        best_ry = ry[min_idx, 0, 0].item()
                        best_theta = theta[min_idx, 0, 0].item()
                        best_color = opt_colors[min_idx].squeeze(-1).squeeze(-1)
                best_cos = math.cos(best_theta)
                best_sin = math.sin(best_theta)
                best_dx = self.x_grid - best_cx
                best_dy = self.y_grid - best_cy
                best_xp = best_dx * best_cos + best_dy * best_sin
                best_yp = -best_dx * best_sin + best_dy * best_cos
                best_mask = ((best_xp / best_rx) ** 2 + (best_yp / best_ry) ** 2 <= 1.0).float()
                canvas = canvas * (1.0 - best_mask) + best_color.unsqueeze(1).unsqueeze(2) * best_mask
                x_json = float((best_cx + 1.0) / 2.0 * 2000.0)
                y_json = float((best_cy + 1.0) / 2.0 * 2000.0)
                sx_json = float(best_rx * 2000.0)
                sy_json = float(best_ry * 2000.0)
                rot_json = float(best_theta * 180.0 / math.pi % 360.0)
                if rot_json < 0.0:
                    rot_json += 360.0
                col_r = max(0, min(255, int(best_color[0].item() * 255.0)))
                col_g = max(0, min(255, int(best_color[1].item() * 255.0)))
                col_b = max(0, min(255, int(best_color[2].item() * 255.0)))
                shapes_json.append({'type': 102, 'data': [x_json, y_json, sx_json, sy_json, rot_json], 'color': [col_r, col_g, col_b, 255]})
                if (layer + 1) % 50 == 0 or layer + 1 == target_layers:
                    progress = (layer + 1) / target_layers * 100.0
                    print(f'  [Progress] Shape {layer + 1:04d}/{target_layers:04d} solved ({progress:.1f}%) | Current L2 Loss: {best_loss:.6f}')
            if gpu_backend == 'directml':
                _ = canvas[0, 0, 0].cpu()
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        print(f'\n[Complete] Successfully generated {target_layers} shapes in {elapsed:.2f} seconds!')
        print(f'Solving Speed: {target_layers / elapsed:.2f} shapes per second.')
        output_root = {'shapes': shapes_json}
        try:
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(output_root, f, indent=4)
            print(f'[Exporter] Successfully exported vector layers to: {output_json}')
            return True
        except Exception as e:
            print(f'[Error] Failed to write output JSON: {e}')
            return False

def import_numpy_array_data_helper(pil_image):
    import numpy as np
    return np.array(pil_image)