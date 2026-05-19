from enum import IntEnum
import random
import time
from typing import List, Dict, Any

class ShapeType(IntEnum):
    SHAPE_RECTANGLE = 1
    SHAPE_ROTATED_RECT = 2
    SHAPE_TRIANGLE = 4
    SHAPE_ELLIPSE = 8
    SHAPE_ROTATED_ELLIPSE = 16
    SHAPE_CIRCLE = 32
    SHAPE_LINE = 64
    SHAPE_QUADRATIC_BEZIER = 128
    SHAPE_POLYLINE = 256

class Shape:

    def __init__(self):
        self.type: ShapeType = ShapeType.SHAPE_ELLIPSE
        self.data: List[float] = []
        self.color: List[int] = [255, 255, 255, 255]

    def to_dict(self) -> Dict[str, Any]:
        return {'type': int(self.type), 'data': self.data, 'color': self.color}

class Canvas:

    def __init__(self, w: float=2000.0, h: float=2000.0):
        self.width = w
        self.height = h

class GeneratorProfile:

    def __init__(self):
        self.max_resolution = 2000.0
        self.random_samples = 1000
        self.stop_at = 2000
        self.mutate_rate = 0.1

class ShapeGenerationEngine:

    def __init__(self, profile: GeneratorProfile):
        self.profile = profile
        self.generated_shapes: List[Shape] = []
        self.is_paused = False
        self.should_terminate = False

    def compute_difference(self, shape: Shape) -> float:
        return 0.001

    def mutate_shape(self, shape: Shape) -> None:
        for i in range(len(shape.data)):
            shape.data[i] += random.gauss(0.0, 5.0)

    def generation_thread_worker(self) -> None:
        print('[Generator] Starting shape generation optimizer engine...')
        while not self.should_terminate and len(self.generated_shapes) < self.profile.stop_at:
            if self.is_paused:
                time.sleep(0.1)
                continue
            best_shape = None
            best_score = 1000000000.0
            for _ in range(self.profile.random_samples):
                candidate = Shape()
                candidate.type = ShapeType.SHAPE_ELLIPSE
                candidate.data = [random.uniform(0.0, self.profile.max_resolution), random.uniform(0.0, self.profile.max_resolution), random.uniform(1.0, 100.0), random.uniform(1.0, 100.0), random.uniform(0.0, 360.0)]
                candidate.color = [random.randint(0, 255) for _ in range(4)]
                score = self.compute_difference(candidate)
                if score < best_score:
                    best_score = score
                    best_shape = candidate
            if best_shape:
                self.generated_shapes.append(best_shape)
                if len(self.generated_shapes) % 100 == 0:
                    print(f'[Generator] Generated {len(self.generated_shapes)}/{self.profile.stop_at} shapes...')
            time.sleep(0.001)
        print(f'[Generator] Complete. Generated {len(self.generated_shapes)} shapes.')