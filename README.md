# Video and Photo to STL

Build a replacement for a rigid household part from ordinary phone photos or video. The Codex plugin guides capture, builds a CAD model, and exports a checked binary STL. Import the STL as millimeters in your slicer.

- **Photos only:** Start with the pictures you have. Codex tells you which view to take next. For a ring, a face-on photo shows its outline and a side photo shows its height. Include one known dimension for scale.
- **Millimeter graph paper:** Place the part on a flat sheet, leave squares visible around it, confirm the small-square spacing, and shoot straight down. Codex can read visible widths, diameters and offsets in the grid plane. A square side photo with the grid level with the side profile can supply thickness. A hidden recess or a tight mating surface may still need one targeted measurement.
- **Video:** Send a short phone video showing all sides, plus photos of any relevant caliper readings. Both Android and iPhone work.

Install the private marketplace and plugin on a computer with Codex and Python 3. Video input also requires FFmpeg.

    codex plugin marketplace add wissamka/spare-part-maker --ref main
    codex plugin add video-and-photo-to-stl@spare-part-tools

In a fresh chat, attach your pictures and ask: **“Use Video and Photo to STL to recreate this part. Each small square is 1 mm. Tell me which other view you need.”** On first use, run the installed skill's scripts/setup to provision its locked Python 3.12 runtime. The same command works from the checked-out skill. Keep each part in a separate job directory. Mesh checks do not replace a physical fit test.
