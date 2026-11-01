"""Export a locally authored CadQuery model and inspect the reloaded STL."""
import argparse
import json
import math
import runpy
import shutil
import struct
import tempfile
from pathlib import Path

import cadquery as cq
import numpy as np
import trimesh
from PIL import Image, ImageDraw


def preview(mesh, path):
    right = np.array([1., -1., 0.]) / math.sqrt(2)
    up = np.array([-1., -1., 2.]) / math.sqrt(6)
    eye = np.cross(up, right)
    xy = mesh.vertices @ np.array([right, -up]).T
    xy -= (xy.min(axis=0) + xy.max(axis=0)) / 2
    xy = xy * (730 / max(np.ptp(xy, axis=0))) + 400
    image = Image.new("RGB", (800, 800), "#fafaf8")
    draw = ImageDraw.Draw(image)
    shade = np.clip(0.70 + 0.28 * (mesh.face_normals @ np.array([.2, -.4, .8])), .30, 1)
    for index in np.argsort(mesh.triangles_center @ eye):
        color = tuple(int(channel * shade[index]) for channel in (100, 165, 190))
        draw.polygon([tuple(p) for p in xy[mesh.faces[index]]], fill=color)
    image.save(path)


def export(model, out, expected):
    build = runpy.run_path(str(model))["build"]
    part = build()
    if isinstance(part, cq.Workplane):
        if part.size() != 1:
            raise ValueError("build() must return one solid")
        part = part.val()
    if not isinstance(part, cq.Shape) or not part.isValid() or len(part.Solids()) != 1:
        raise ValueError("CAD must contain one valid solid per output file")
    stl = out / "part.stl"
    part.exportStl(str(stl), tolerance=0.015, angularTolerance=0.08, ascii=False, relative=False)
    with stl.open("rb") as stream:
        stream.seek(80)
        triangle_count, = struct.unpack("<I", stream.read(4))
    if stl.stat().st_size != 84 + triangle_count * 50:
        raise ValueError("Invalid binary STL length")
    mesh = trimesh.load_mesh(stl, process=True)
    components = mesh.split(only_watertight=False)
    # A valid solid can have an outer shell and enclosed inner voids.
    if (not mesh.is_volume or not np.isfinite(mesh.vertices).all()
            or any(not shell.is_watertight for shell in components)):
        raise ValueError("Export is not a finite, consistently wound closed volume")
    if not np.allclose(mesh.extents, expected, atol=0.05, rtol=0):
        raise ValueError(f"STL bounds {mesh.extents} disagree with intended XYZ {expected} mm")
    if not np.isclose(mesh.volume, part.Volume(), rtol=0.005, atol=0.02):
        raise ValueError("Mesh volume disagrees with CAD volume")
    report = dict(units="mm", expected_xyz_mm=expected, actual_xyz_mm=mesh.extents.tolist(),
                  triangles=triangle_count, cad_solids=1, mesh_shells=len(components),
                  volume_mm3=float(mesh.volume), watertight=bool(mesh.is_watertight),
                  consistent_winding=bool(mesh.is_winding_consistent), physical_fit="untested")
    preview(mesh, out / "preview.png")
    shutil.copyfile(model, out / "model.py")
    (out / "validation.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("model", type=Path, help="Trusted local Python file defining build()")
    p.add_argument("output", type=Path, help="New revision directory")
    p.add_argument("--size", required=True, nargs=3, type=float, metavar=("X", "Y", "Z"))
    args = p.parse_args()
    if args.output.exists() or not all(math.isfinite(n) and n > 0 for n in args.size):
        p.error("Provide a new output directory and three positive dimensions in mm")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
        out = Path(tmp) / "revision"
        out.mkdir()
        export(args.model, out, args.size)
        out.rename(args.output)
    print(f"{args.output / 'part.stl'} | import as millimeters")
