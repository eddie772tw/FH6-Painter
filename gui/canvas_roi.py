import tkinter as tk


class CanvasROIMixin:
    def _is_roi_allowed(self):
        """Check all preconditions for ROI selection."""
        if self.is_generating or self.is_importing:
            return False
        if not self.render_meta:
            return False
        if not self.has_completed_generation:
            return False
        if not self.var_roi_enabled.get():
            return False
        if not self.enable_preview:
            return False

        # Check if engine is GO_OPENCL
        if hasattr(self, "combo_engine") and hasattr(self, "available_evaluators"):
            engine_idx = self.combo_engine.current()
            engine_code = (
                self.available_evaluators[engine_idx]["code"]
                if 0 <= engine_idx < len(self.available_evaluators)
                else "NUMBA"
            )
            if engine_code == "GO_OPENCL":
                return False

        return True

    def _point_in_roi(self, px, py):
        """Check if a point is inside the current selection ROI on canvas."""
        if not self.selection_roi:
            return False
        x1, y1, x2, y2 = self.selection_roi
        lx, rx = min(x1, x2), max(x1, x2)
        ly, ry = min(y1, y2), max(y1, y2)
        return lx <= px <= rx and ly <= py <= ry

    def _redraw_roi_shape(self):
        """Redraw the ROI overlay on the canvas using current shape mode and coordinates."""
        if getattr(self, "selection_rect_id", None):
            self.canvas_preview.delete(self.selection_rect_id)
            self.selection_rect_id = None
        if not self.selection_roi:
            return
        x1, y1, x2, y2 = self.selection_roi
        shape_mode = self.var_roi_shape.get()
        if shape_mode == "ellipse":
            self.selection_rect_id = self.canvas_preview.create_oval(
                x1,
                y1,
                x2,
                y2,
                outline="#FF4444",
                width=2,
                dash=(4, 4),
            )
        else:
            self.selection_rect_id = self.canvas_preview.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                outline="#FF4444",
                width=2,
                dash=(4, 4),
            )

    def _update_roi_range_label(self):
        """Sync the range label in the control card with current ROI state."""
        if not hasattr(self, "lbl_roi_range"):
            return
        if self.selection_roi:
            x1, y1, x2, y2 = self.selection_roi
            mode_label = "橢圓" if self.var_roi_shape.get() == "ellipse" else "矩形"
            self.lbl_roi_range.configure(
                text=f"({x1},{y1}) → ({x2},{y2})  [{mode_label}]",
                fg=self.color_green,
            )
        else:
            self.lbl_roi_range.configure(text="尚未選取", fg="#888888")

    def on_canvas_press(self, event):
        if not self._is_roi_allowed():
            return
        # Check if clicking inside an existing ROI to drag it
        if self.selection_roi and self._point_in_roi(event.x, event.y):
            self._roi_dragging = True
            self._roi_drag_start_x = event.x
            self._roi_drag_start_y = event.y
            return

        # Otherwise start a new selection
        self._roi_dragging = False
        self.selection_start_x = event.x
        self.selection_start_y = event.y
        if getattr(self, "selection_rect_id", None):
            self.canvas_preview.delete(self.selection_rect_id)
        shape_mode = self.var_roi_shape.get()
        if shape_mode == "ellipse":
            self.selection_rect_id = self.canvas_preview.create_oval(
                event.x,
                event.y,
                event.x,
                event.y,
                outline="#FF4444",
                width=2,
                dash=(4, 4),
            )
        else:
            self.selection_rect_id = self.canvas_preview.create_rectangle(
                event.x,
                event.y,
                event.x,
                event.y,
                outline="#FF4444",
                width=2,
                dash=(4, 4),
            )

    def on_canvas_drag(self, event):
        if not self._is_roi_allowed():
            return

        if getattr(self, "_roi_dragging", False) and self.selection_roi:
            # Drag-move the existing selection
            dx = event.x - self._roi_drag_start_x
            dy = event.y - self._roi_drag_start_y
            x1, y1, x2, y2 = self.selection_roi
            self.selection_roi = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)
            self._roi_drag_start_x = event.x
            self._roi_drag_start_y = event.y
            # Update canvas shape
            if getattr(self, "selection_rect_id", None):
                self.canvas_preview.coords(
                    self.selection_rect_id,
                    self.selection_roi[0],
                    self.selection_roi[1],
                    self.selection_roi[2],
                    self.selection_roi[3],
                )
            self._update_roi_range_label()
            return

        # Drawing a new selection
        if getattr(self, "selection_rect_id", None):
            self.canvas_preview.coords(
                self.selection_rect_id,
                self.selection_start_x,
                self.selection_start_y,
                event.x,
                event.y,
            )

    def on_canvas_release(self, event):
        if not self._is_roi_allowed():
            return

        # If we were dragging, just finalize
        if getattr(self, "_roi_dragging", False):
            self._roi_dragging = False
            shape_mode = self.var_roi_shape.get()
            mode_label = "橢圓" if shape_mode == "ellipse" else "矩形"
            self.log_to_console(f"ROI Moved ({mode_label}): {self.selection_roi}\n")
            self._update_roi_range_label()
            return

        # Store RAW canvas coordinates
        x1 = self.selection_start_x
        y1 = self.selection_start_y
        x2 = event.x
        y2 = event.y

        # Don't save if the box is too small (e.g. just a click)
        if abs(x2 - x1) > 5 and abs(y2 - y1) > 5:
            self.selection_roi = (x1, y1, x2, y2)
            shape_mode = self.var_roi_shape.get()
            mode_label = "橢圓" if shape_mode == "ellipse" else "矩形"
            self.log_to_console(f"ROI Selected ({mode_label}): {self.selection_roi}\n")
        else:
            self.selection_roi = None
            if getattr(self, "selection_rect_id", None):
                self.canvas_preview.delete(self.selection_rect_id)
                self.selection_rect_id = None
        self._update_roi_range_label()

    def on_canvas_right_click(self, event):
        self.selection_roi = None
        if getattr(self, "selection_rect_id", None):
            self.canvas_preview.delete(self.selection_rect_id)
            self.selection_rect_id = None
        self.log_to_console("ROI Cleared.\n")
        self._update_roi_range_label()

    def on_roi_shape_changed(self):
        """Called when the user switches between rectangle and ellipse mode."""
        if self.selection_roi:
            self._redraw_roi_shape()
            self._update_roi_range_label()

    def on_roi_toggle_changed(self):
        """Handle the ROI enable/disable toggle in the control card."""
        enabled = self.var_roi_enabled.get()
        if enabled and self.has_completed_generation:
            self.lbl_roi_status.configure(
                text="已啟用 — 可框選區域", fg=self.color_green
            )
        elif enabled and not self.has_completed_generation:
            self.lbl_roi_status.configure(text="等待首次生成完成", fg="#888888")
        else:
            # User manually disabled
            self.lbl_roi_status.configure(
                text="已停用 — 將進行全域重新生成", fg="#FFA500"
            )
            # Clear any existing ROI when disabled
            self.selection_roi = None
            if getattr(self, "selection_rect_id", None):
                self.canvas_preview.delete(self.selection_rect_id)
                self.selection_rect_id = None
            if hasattr(self, "lbl_roi_range"):
                self.lbl_roi_range.configure(text="尚未選取", fg="#888888")

    def update_roi_status_label(self):
        """Refresh the ROI status label to reflect current state."""
        if not hasattr(self, "lbl_roi_status"):
            return
        if not self.has_completed_generation:
            self.lbl_roi_status.configure(text="等待首次生成完成", fg="#888888")
        elif self.var_roi_enabled.get():
            self.lbl_roi_status.configure(
                text="已啟用 — 可框選區域", fg=self.color_green
            )
        else:
            self.lbl_roi_status.configure(
                text="已停用 — 將進行全域重新生成", fg="#FFA500"
            )
