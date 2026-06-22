import os
import tkinter as tk

from gui.utils import get_project_root


class TimelineMixin:
    def on_timeline_click(self, event):
        if self.is_generating or self.is_importing:
            return
        if not getattr(self, "available_checkpoints", None):
            self.scan_checkpoints()
            if not getattr(self, "available_checkpoints", None):
                self.log_to_console(
                    "[Timeline] No checkpoints found for the current project.\n"
                )
                return

        w = self.progress_bar.winfo_width()
        if w <= 0:
            return
        pct = event.x / w

        try:
            total_layers = int(self.val_layers.get())
        except ValueError:
            total_layers = 1000

        target_layer = max(1, int(pct * total_layers))

        best_cp = None
        for cp in sorted(self.available_checkpoints.keys()):
            if cp >= target_layer:
                best_cp = cp
                break
        if not best_cp:
            best_cp = max(self.available_checkpoints.keys())

        if best_cp:
            self.log_to_console(
                f"[Timeline] Scrubbing to layer {target_layer} (Using checkpoint {best_cp})\n"
            )
            if hasattr(self, "val_rewind_layer"):
                self.val_rewind_layer.set(str(target_layer))
            if hasattr(self, "lbl_rewind_hint"):
                self.lbl_rewind_hint.configure(
                    text=f"(checkpoint {best_cp})", fg=self.color_blue
                )
            self.load_checkpoint_preview(
                self.available_checkpoints[best_cp], target_layer
            )

    def on_manual_rewind(self):
        """Handle the manual rewind button click from the Region Painting card."""
        if self.is_generating or self.is_importing:
            return

        if not getattr(self, "available_checkpoints", None):
            self.scan_checkpoints()
            if not getattr(self, "available_checkpoints", None):
                if hasattr(self, "lbl_rewind_hint"):
                    self.lbl_rewind_hint.configure(text="找不到檢查點", fg="#D32F2F")
                return

        try:
            target_layer = int(self.val_rewind_layer.get().strip())
        except ValueError:
            if hasattr(self, "lbl_rewind_hint"):
                self.lbl_rewind_hint.configure(text="請輸入有效的數字", fg="#D32F2F")
            return

        if target_layer < 1:
            if hasattr(self, "lbl_rewind_hint"):
                self.lbl_rewind_hint.configure(text="層數必須 ≥ 1", fg="#D32F2F")
            return

        best_cp = None
        for cp in sorted(self.available_checkpoints.keys()):
            if cp >= target_layer:
                best_cp = cp
                break
        if not best_cp:
            best_cp = max(self.available_checkpoints.keys())

        self.log_to_console(
            f"[Timeline] Manual rewind to layer {target_layer} (Using checkpoint {best_cp})\n"
        )
        if hasattr(self, "lbl_rewind_hint"):
            self.lbl_rewind_hint.configure(
                text=f"(checkpoint {best_cp})", fg=self.color_blue
            )
        self.load_checkpoint_preview(self.available_checkpoints[best_cp], target_layer)

    def load_checkpoint_preview(self, filepath, slice_layer):
        import json

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            shapes = data.get("shapes", [])
            sliced_shapes = shapes[: slice_layer + 1]

            temp_path = os.path.join(os.path.dirname(filepath), "_temp_resume.json")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump({"shapes": sliced_shapes}, f)

            self.auto_load_json_path = temp_path
            self.entry_file_path.delete(0, tk.END)
            self.entry_file_path.insert(0, temp_path)
            self.on_file_changed()

            self.log_to_console(
                f"[Timeline] Loaded preview at layer {slice_layer}. You can now start generation to branch from here.\n"
            )
        except Exception as e:
            self.log_to_console(f"ERROR reading checkpoint: {e}\n")

    def scan_checkpoints(self):
        img_path = self.entry_file_path.get().strip()
        if not img_path:
            return
        img_base = os.path.splitext(os.path.basename(img_path))[0]
        if img_base.endswith("_masked"):
            img_base = img_base[:-7]

        if img_base != "_temp_resume":
            self.available_checkpoints = {}
            output_dir = os.path.join(get_project_root(), "output", img_base)
            if os.path.exists(output_dir):
                import glob

                for f in glob.glob(os.path.join(output_dir, f"{img_base}_*.json")):
                    basename = os.path.basename(f)
                    num_str = basename.replace(img_base + "_", "").replace(".json", "")
                    try:
                        num = int(num_str)
                        self.available_checkpoints[num] = f
                    except Exception:
                        pass

            if img_path.lower().endswith(".json") and os.path.exists(img_path):
                try:
                    import json

                    with open(img_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    num_layers = max(0, len(data.get("shapes", [])) - 1)
                    if num_layers > 0:
                        self.available_checkpoints[num_layers] = img_path
                except Exception:
                    pass

        self.timeline_canvas.delete("all")
        if not getattr(self, "available_checkpoints", None):
            return

        w = self.timeline_canvas.winfo_width()
        h = self.timeline_canvas.winfo_height()
        if w <= 1:
            w = 380

        max_cp = max(self.available_checkpoints.keys())
        total_layers = max_cp if max_cp > 0 else 1000

        for cp in self.available_checkpoints.keys():
            x = (cp / total_layers) * w
            self.timeline_canvas.create_line(x, 0, x, h, fill=self.color_blue, width=2)
