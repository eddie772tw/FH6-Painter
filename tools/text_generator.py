import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def generate_text_shapes(
    text, font_path, font_size, color=(255, 255, 255, 255), canvas_w=512, canvas_h=512
):
    """Generates rectangle shapes for the given text using Pillow (Row compression approach)."""
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        # Fallback to default if not found
        font = ImageFont.load_default()

    # Create a blank image
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw text centered
    try:
        draw.text(
            (canvas_w // 2, canvas_h // 2), text, font=font, fill=color, anchor="mm"
        )
    except TypeError:
        # Older Pillow fallback
        draw.text((canvas_w // 2, canvas_h // 2), text, font=font, fill=color)

    arr = np.array(img)
    shapes = []

    # Header shape
    shapes.append(
        {
            "type": 1,
            "data": [0.0, 0.0, float(canvas_w), float(canvas_h)],
            "color": [0, 0, 0, 0],
            "score": 0.0,
        }
    )

    # Row compression: combine adjacent horizontal pixels into a single rectangle
    for y in range(canvas_h):
        start_x = -1
        for x in range(canvas_w):
            alpha = arr[y, x, 3]
            if alpha > 127:
                if start_x == -1:
                    start_x = x
            else:
                if start_x != -1:
                    w = x - start_x
                    h = 1.0
                    cx = start_x + w / 2.0
                    cy = y + 0.5
                    # type 1 is rectangle (Square in FH6)
                    shapes.append(
                        {
                            "type": 1,
                            "data": [float(cx), float(cy), float(w), float(h), 0.0],
                            "color": [
                                int(arr[y, start_x, 0]),
                                int(arr[y, start_x, 1]),
                                int(arr[y, start_x, 2]),
                                255,
                            ],
                            "score": 0.0,
                        }
                    )
                    start_x = -1

        if start_x != -1:
            w = canvas_w - start_x
            h = 1.0
            cx = start_x + w / 2.0
            cy = y + 0.5
            shapes.append(
                {
                    "type": 1,
                    "data": [float(cx), float(cy), float(w), float(h), 0.0],
                    "color": [
                        int(arr[y, start_x, 0]),
                        int(arr[y, start_x, 1]),
                        int(arr[y, start_x, 2]),
                        255,
                    ],
                    "score": 0.0,
                }
            )

    return {"shapes": shapes}


def save_text_json(text, font_path, font_size, out_path, color=(255, 255, 255, 255)):
    data = generate_text_shapes(text, font_path, font_size, color)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
