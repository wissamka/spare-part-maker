import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins/video-and-photo-to-stl/skills/video-and-photo-to-stl/scripts"


class GridPhoto(unittest.TestCase):
    def test_perspective_photo_and_miscount(self):
        # Render a planar 16 x 8 mm plate on 2 mm paper under perspective.
        def px(x, y):
            d = 1 + 0.006*x + 0.003*y
            return [round((30 + 13*x + 0.5*y)/d), round((20 + x + 12*y)/d)]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            photo = root/"plate.png"
            im = Image.new("RGB", (490,280), "white")
            draw = ImageDraw.Draw(im)
            for x in range(0,41,2):
                draw.line([tuple(px(x,0)),tuple(px(x,20))], fill="gray")
            for y in range(0,21,2):
                draw.line([tuple(px(0,y)),tuple(px(40,y))], fill="gray")
            draw.polygon([tuple(px(x,y)) for x,y in [(10,6),(26,6),(26,14),(10,14)]], fill="black")
            im.save(photo)
            ev = root/"evidence"
            subprocess.run([sys.executable, SCRIPTS/"capture.py",ev,photo], check=True)
            spec = dict(pitch_mm=2, rectangle_cells=[20,10],
                        corners_px=[px(0,0),px(40,0),px(40,20),px(0,20)],
                        check_cells=[2,3],check_px=px(4,6),
                        spans_px={"width":[px(10,6),px(26,6)],"height":[px(10,6),px(10,14)]})
            picks = root/"points.json"
            command = [sys.executable, SCRIPTS/"grid.py",ev/"photo-001.png",picks]
            picks.write_text(json.dumps(spec))
            result = json.loads(subprocess.check_output(command))
            self.assertAlmostEqual(result["spans_mm"]["width"], 16, delta=.15)
            self.assertAlmostEqual(result["spans_mm"]["height"], 8, delta=.15)
            spec["check_cells"]=[3,3]
            picks.write_text(json.dumps(spec))
            proc = subprocess.run(command, capture_output=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(b"Grid check misses", proc.stderr)
            self.assertFalse(proc.stdout)
