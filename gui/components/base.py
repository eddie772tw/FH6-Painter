import tkinter as tk
from tkinter import ttk


def create_card_header(parent, title, subtitle, app):
    """Creates a standardized modern card header inside custom panels."""
    header_frame = tk.Frame(parent, bg=app.bg_card)
    header_frame.pack(fill="x", padx=15, pady=(10, 5))

    lbl_title = ttk.Label(header_frame, text=title, style="Title.TLabel")
    lbl_title.pack(anchor="w")

    lbl_sub = ttk.Label(header_frame, text=subtitle, style="Text.TLabel")
    lbl_sub.pack(anchor="w")

    # Cyber subtle accent line
    accent = tk.Frame(parent, bg=app.border_color, height=1)
    accent.pack(fill="x", padx=15, pady=(2, 5))


def draw_cyber_placeholder(app, text="STUDIO READY"):
    """Draws a clean, dark tech cyberpunk graphic when no active simulation is running."""
    app.preview_image_id = None
    app.canvas_preview.delete("all")

    canvas_w = app.canvas_preview.winfo_width()
    canvas_h = app.canvas_preview.winfo_height()
    if canvas_w <= 1 or canvas_h <= 1:
        canvas_w = 380
        canvas_h = 380

    # 保持正方形區域繪製 grid
    size = min(canvas_w, canvas_h)
    offset_x = (canvas_w - size) / 2
    offset_y = (canvas_h - size) / 2

    # Cyber grid lines within square region
    for i in range(10):
        gap = size / 10
        # Horizontal lines
        app.canvas_preview.create_line(
            offset_x,
            offset_y + i * gap,
            offset_x + size,
            offset_y + i * gap,
            fill="#151515",
            width=1,
        )
        # Vertical lines
        app.canvas_preview.create_line(
            offset_x + i * gap,
            offset_y,
            offset_x + i * gap,
            offset_y + size,
            fill="#151515",
            width=1,
        )

    # Circular HUD radar lines
    center_x = canvas_w / 2
    center_y = canvas_h / 2

    radar_radius = size * 0.4
    app.canvas_preview.create_oval(
        center_x - radar_radius,
        center_y - radar_radius,
        center_x + radar_radius,
        center_y + radar_radius,
        outline="#222222",
        width=1,
    )
    app.canvas_preview.create_oval(
        center_x - radar_radius * 0.67,
        center_y - radar_radius * 0.67,
        center_x + radar_radius * 0.67,
        center_y + radar_radius * 0.67,
        outline="#2A2A2A",
        width=1,
    )
    app.canvas_preview.create_oval(
        center_x - radar_radius * 0.27,
        center_y - radar_radius * 0.27,
        center_x + radar_radius * 0.27,
        center_y + radar_radius * 0.27,
        outline="#333333",
        width=1,
    )

    # Crosshair lines
    cross_len = radar_radius * 1.07
    app.canvas_preview.create_line(
        center_x - cross_len,
        center_y,
        center_x - 10,
        center_y,
        fill="#333333",
        width=1,
    )
    app.canvas_preview.create_line(
        center_x + 10,
        center_y,
        center_x + cross_len,
        center_y,
        fill="#333333",
        width=1,
    )
    app.canvas_preview.create_line(
        center_x,
        center_y - cross_len,
        center_x,
        center_y - 10,
        fill="#333333",
        width=1,
    )
    app.canvas_preview.create_line(
        center_x,
        center_y + 10,
        center_x,
        center_y + cross_len,
        fill="#333333",
        width=1,
    )

    # Text label in center
    app.canvas_preview.create_text(
        center_x,
        center_y,
        text=text,
        fill=app.fg_secondary,
        font=("Outfit", 10, "bold"),
    )
    app.canvas_preview.create_text(
        center_x,
        center_y + 25,
        text="LOAD INPUT DATA FILE",
        fill="#555555",
        font=("Microsoft JhengHei", 8),
    )
