import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image
from pillow_heif import register_heif_opener

SKILL = Path(__file__).resolve().parents[1] / "plugins/video-and-photo-to-stl/skills/video-and-photo-to-stl"
SCRIPTS = SKILL / "scripts"
spec = importlib.util.spec_from_file_location("export_part", SCRIPTS / "export_part.py")
export_part = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export_part)

CASES = {
    "spacer": ("cq.Workplane('XY').circle(12).circle(5).extrude(8)", [24, 24, 8]),
    "bracket": ("cq.Workplane('XY').box(36, 16, 4, centered=(True,True,False))"
                ".faces('>Z').workplane().pushPoints([(-10,0),(10,0)]).hole(4)"
                ".union(cq.Workplane('XY').box(4,16,20,centered=(True,True,False)).translate((-16,0,0)))",
                [36, 16, 20]),
    "cover": ("cq.Workplane('XY').box(30,20,2,centered=(True,True,False))"
              ".union(cq.Workplane('XY').workplane(offset=2).rect(26,16).rect(22,12).extrude(3))",
              [30, 20, 5]),
}


def make_model(root, name, expression, size):
    model = root / f"{name}.py"
    model.write_text("import cadquery as cq\n\ndef build():\n    return " + expression + "\n")
    dest = root / name
    dest.mkdir()
    export_part.export(model, dest, size)
    return trimesh.load_mesh(dest / "part.stl")


class Workflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.addCleanup(self.temp.cleanup)

    def test_parts_and_fit_revision(self):
        meshes = {key: make_model(self.root, key, *case) for key, case in CASES.items()}
        x = np.linalg.norm(meshes["spacer"].vertices[:, :2], axis=1)
        self.assertAlmostEqual(x.min(), 5, places=3)
        m = make_model(self.root, "revision", CASES["spacer"][0].replace("circle(5)", "circle(5.2)"), [24,24,8])
        self.assertAlmostEqual(np.linalg.norm(m.vertices[:,:2], axis=1).min(), 5.2, places=3)
        self.assertTrue(np.allclose(m.extents, meshes["spacer"].extents))
        br = meshes["bracket"].section(plane_origin=[0,0,2], plane_normal=[0,0,1])
        centers = sorted(np.round((p.min(axis=0)+p.max(axis=0))/2, 2)[0] for p in br.discrete)
        self.assertEqual(centers, [-10,0,10])
        lip = meshes["cover"].section(plane_origin=[0,0,4], plane_normal=[0,0,1])
        self.assertEqual(sorted(round(np.ptp(p[:,0])) for p in lip.discrete), [22,26])

    def test_wrong_scale_does_not_publish(self):
        model = self.root / "m.py"
        model.write_text("import cadquery as cq\ndef build(): return cq.Workplane().box(1,2,3)")
        dest = self.root / "rev"
        result = subprocess.run([sys.executable, SCRIPTS/"export_part.py", model, dest, "--size", "25.4", "2", "3"], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(dest.exists())

    def test_phone_formats_and_evidence(self):
        register_heif_opener()
        raw = self.root / "raw.mp4"
        mov = self.root / "rotated.mov"
        cli = ["ffmpeg", "-loglevel", "error", "-nostdin"]
        subprocess.run(cli + ["-f","lavfi","-i","testsrc2=s=160x96:r=12:d=3","-c:v","libx264",str(raw)], check=True)
        subprocess.run(cli + ["-display_rotation","90","-i",str(raw),"-c","copy",str(mov)], check=True)
        photo = self.root / "caliper.heic"
        Image.new("RGB",(200,100),"gray").save(photo, format="HEIF")
        dest = self.root / "evidence"
        proc = [sys.executable, SCRIPTS/"capture.py",dest,raw,mov,photo]
        subprocess.run(proc, check=True)
        rows = json.loads((dest/"frames.json").read_text())
        turned = [r for r in rows if r["source"] == str(mov)]
        self.assertTrue(turned)
        self.assertEqual(sorted(r["seconds"] for r in turned), [r["seconds"] for r in turned])
        with Image.open(dest/turned[0]["image"]) as im:
            self.assertGreater(im.height, im.width)
        self.assertEqual(rows[-1]["source"], str(photo))
        self.assertTrue((dest/"contact-sheet.jpg").exists())
        self.assertNotEqual(subprocess.run(proc, capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
