#!/usr/bin/env python3
import json
import math
import sys


def verify_boundary(json_path, w=600.0, h=600.0):
    print(f"Loading {json_path}...")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load JSON file: {e}")
        return False

    shapes = data.get("shapes", [])
    print(f"Total shapes: {len(shapes)}")

    ok = True
    errors = []
    shapes_checked = 0

    for idx, s in enumerate(shapes):
        # We only check type 32 (ellipse). Skip background or reset redundant shapes (color transparency 0/left-top 0,0)
        if s.get("type") == 32:
            d = s.get("data", [])
            if len(d) < 5:
                continue

            x_c, y_c, r_x, r_y, theta_deg = d[0], d[1], d[2], d[3], d[4]

            # Skip if it is a reset/redundant shape at (0, 0)
            if x_c == 0.0 and y_c == 0.0 and r_x == 2.0 and r_y == 2.0:
                continue

            shapes_checked += 1
            theta = math.radians(theta_deg)
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)

            # Exact half-widths of the bounding box of the rotated ellipse
            x_h = math.sqrt(r_x**2 * cos_t**2 + r_y**2 * sin_t**2)
            y_h = math.sqrt(r_x**2 * sin_t**2 + r_y**2 * cos_t**2)

            min_x = x_c - x_h
            max_x = x_c + x_h
            min_y = y_c - y_h
            max_y = y_c + y_h

            # Allow for very tiny floating point precision issues (e.g. 1e-4)
            tolerance = 1e-4
            if (
                min_x < -tolerance
                or max_x > w + tolerance
                or min_y < -tolerance
                or max_y > h + tolerance
            ):
                ok = False
                errors.append(
                    {
                        "index": idx,
                        "center": (x_c, y_c),
                        "rx_ry": (r_x, r_y),
                        "theta": theta_deg,
                        "x_range": (min_x, max_x),
                        "y_range": (min_y, max_y),
                    }
                )

    print("Verification Results:")
    print(f"Checked shapes (non-background, non-redundant): {shapes_checked}")
    if ok:
        print(
            "VERIFICATION SUCCESSFUL! All ellipses are 100% inside the canvas boundary."
        )
        return True
    else:
        print(
            f"VERIFICATION FAILED! Found {len(errors)} shapes violating the boundary limits."
        )
        for err in errors:
            print(f"  Shape index {err['index']}:")
            print(
                f"    Center: {err['center']}, Radii: {err['rx_ry']}, Theta: {err['theta']}"
            )
            print(
                f"    X Range: [{err['x_range'][0]:.4f}, {err['x_range'][1]:.4f}] (Canvas Width: {w})"
            )
            print(
                f"    Y Range: [{err['y_range'][0]:.4f}, {err['y_range'][1]:.4f}] (Canvas Height: {h})"
            )
        return False


if __name__ == "__main__":
    json_file = "output/test_boundary/test_boundary.json"
    if len(sys.argv) > 1:
        json_file = sys.argv[1]

    success = verify_boundary(json_file)
    sys.exit(0 if success else 1)
