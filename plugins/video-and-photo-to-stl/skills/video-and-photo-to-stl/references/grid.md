# Read a dimension from graph paper

Codex chooses the points; the person taking photos need not annotate anything. Work from the oriented photo-NNN.png, never a contact-sheet thumbnail. Confirm the physical pitch of the intervals you count. Establish which edge is in the paper's plane: calibrating paper cannot correct parallax on a raised rim. For a raised or hidden critical feature ask for a same-height reference, a square side view, or that one caliper reading. Never infer depth from a top view.

1. Identify four visible intersections forming a rectangle around the feature. Start at an origin and follow the perimeter: along the first grid axis, across the second, then back parallel to the first. Count intervals, not lines. Select a fifth visible interior intersection separately as a check. Use a tighter view or request a retake if the lines cannot be distinguished. Do not invent pixel coordinates from a verbal description.
2. Make a job-local picks JSON for each view. All pixels are [x,y] from the top left of the full-size oriented PNG. The example below illustrates a 20 × 16 interval rectangle on 1 mm paper. Replace every point and count from the actual photo.
```json
{"pitch_mm":1,"rectangle_cells":[20,16],
 "corners_px":[[20,30],[220,30],[220,190],[20,190]],
 "check_cells":[2,3],"check_px":[40,60],
 "spans_px":{"outer_width":[[45,110],[195,110]]}}
```

3. Run `scripts/run grid evidence-01/photo-001.png picks.json > grid-report.json`. It maps the selected endpoints onto the paper, checks the independent intersection, and reports the distance in millimeters. A failed check means re-inspect the picks or retake the view. Four corners alone cannot validate a calibration. A passing check does not certify the paper's pitch, the feature plane, or physical fit.
4. Record the source image, grid pitch, endpoints and result in measurements.md. Estimate the range by repeating plausible edge picks at the limits of blur and cross-check against another view when available. Round to what the image supports. If the range exceeds the fit tolerance or views disagree, request the specific missing measurement. Do not export a fit-critical dimension as verified just because the calculation has decimals.
