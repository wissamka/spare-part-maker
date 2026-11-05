"""Measure same-plane spans selected by Codex on one full-resolution grid photo."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def measure(spec, image_path):
    with Image.open(image_path) as image:
        width, height = image.size

    def pixels(value, count):
        p = np.asarray(value, dtype=float)
        if (p.shape != (count, 2) or not np.isfinite(p).all() or
                np.any(p < 0) or np.any(p >= [width, height])):
            raise ValueError("Expected full-image pixel coordinates inside the photo.")
        return p

    pitch = float(spec["pitch_mm"])
    cells = np.asarray(spec["rectangle_cells"], dtype=float)
    if (not np.isfinite(pitch) or pitch <= 0 or cells.shape != (2,) or
            not np.isfinite(cells).all() or (cells < 2).any() or (cells != np.floor(cells)).any()):
        raise ValueError("Use a known positive pitch and a rectangle spanning multiple whole cells.")
    w, h = cells * pitch
    quad = pixels(spec["corners_px"], 4)
    edges = np.roll(quad, -1, axis=0) - quad
    def cross(a, b):
        return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]
    turns = cross(edges, np.roll(edges, -1, axis=0))
    if not ((turns > 0).all() or (turns < 0).all()):
        raise ValueError("Use four distinct corners of a convex rectangle in perimeter order.")
    # Shift origin to the first intersection so the homography has finite scale there.
    a, b = [], []
    for (x, y), (u, v) in zip(quad - quad[0], [(0, 0), (w, 0), (w, h), (0, h)]):
        a.extend([[x,y,1,0,0,0,-u*x,-u*y], [0,0,0,x,y,1,-v*x,-v*y]])
        b.extend([u, v])
    mat = np.append(np.linalg.solve(a, b), 1).reshape(3, 3)

    def project(p):
        if np.any(np.sign(turns[0]) * cross(edges, p - quad) < -1e-7):
            raise ValueError("Select points inside the calibrated grid rectangle.")
        q = mat @ np.r_[p - quad[0], 1]
        return q[:2] / q[2]

    check = np.asarray(spec["check_cells"], dtype=float)
    if (check.shape != (2,) or not np.isfinite(check).all() or
            (check != np.floor(check)).any() or (check <= 0).any() or (check >= cells).any()):
        raise ValueError("Check an independent interior grid intersection.")
    check_mm = project(pixels([spec["check_px"]], 1)[0])
    error = float(np.linalg.norm(check_mm - pitch * check))
    if error > pitch * 0.25:
        raise ValueError("Grid check misses by more than a quarter cell. Recheck pitch, counts and points.")
    spans = {}
    for label, pair in spec["spans_px"].items():
        start, end = map(project, pixels(pair, 2))
        length = float(np.linalg.norm(end - start))
        if length <= 0:
            raise ValueError("Span endpoints coincide.")
        spans[label] = length
    if not spans:
        raise ValueError("Select at least one span.")
    return dict(image=str(image_path), method="same-plane grid estimate",
                check_error_mm=error, spans_mm=spans, picks=spec)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Oriented evidence PNG")
    parser.add_argument("picks", type=Path, help="Calibration and feature pixels in JSON")
    args = parser.parse_args()
    try:
        print(json.dumps(measure(json.loads(args.picks.read_text()), args.image), indent=2, allow_nan=False))
    except (ValueError, TypeError, KeyError, OSError, np.linalg.LinAlgError) as exc:
        parser.exit(2, f"Cannot measure this view: {exc}\n")
