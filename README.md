# Video and Photo to STL

Install the private marketplace and plugin on a computer with Codex, Python 3 and FFmpeg.

    codex plugin marketplace add wissamka/spare-part-maker --ref main
    codex plugin add video-and-photo-to-stl@spare-part-tools

Open a fresh chat, attach the original phone video and caliper photos, and ask Video and Photo to STL to build a replacement part. The skill guides capture, records the measured features, authors the CAD model and exports a checked binary STL. On first use, run the installed skill's scripts/setup to provision its locked Python 3.12 runtime. For development, the same command works from the checked-out skill. Use a separate directory for each part. Import exported STLs as millimeters.
