"""Prepare reviewable stills, a contact sheet and a source index for one part."""
import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps
from pillow_heif import register_heif_opener


def signature(path):
    with Image.open(path) as im:
        sample = np.asarray(im.convert("L").resize((96, 96)), dtype=float)
    center = sample[1:-1, 1:-1]
    laplace = (sample[:-2, 1:-1] + sample[2:, 1:-1] +
               sample[1:-1, :-2] + sample[1:-1, 2:] - 4 * center)
    return sample, float(laplace.var())


def video_candidates(path, scratch, args):
    if not shutil.which("ffmpeg"):
        raise ValueError("Video capture requires FFmpeg. Install it or provide still photos.")
    limits = []
    if args.start:
        limits.append(f"gte(t,{args.start})")
    if args.end is not None:
        limits.append(f"lte(t,{args.end})")
    limits.append(f"(isnan(prev_selected_t)+gte(t-prev_selected_t,{1 / args.fps}))")
    select = "*".join(limits)
    # showinfo after select retains presentation times, including variable-rate footage.
    filters = f"select='{select}',showinfo,scale='min(1600,iw)':-2"
    command = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "info",
               "-protocol_whitelist", "file", "-i", str(path), "-map", "0:v:0",
               "-an", "-vf", filters, "-fps_mode", "vfr", "-q:v", "2",
               str(scratch / "%06d.jpg")]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"Cannot decode {path.name}: {result.stderr[-650:]}")
    times = re.findall(r"\bn:\s*\d+\s+pts:\s*-?\d+\s+pts_time:([-+.\deE]+)", result.stderr)
    files = sorted(scratch.glob("*.jpg"))
    if not files or len(files) != len(times):
        raise ValueError(f"No timestamped frames in requested interval of {path.name}")
    frames = []
    for filename, time in zip(files, times):
        sample, sharpness = signature(filename)
        frames.append((filename, float(time), sample, sharpness))
    return frames


def pick(frames, limit):
    # Keep time coverage even when one face is sharper than every other face.
    bins = np.array_split(np.arange(len(frames)), min(limit, len(frames)))
    selected = []
    for indices in bins:
        ranked = sorted((frames[i] for i in indices), key=lambda f: -f[3])
        for candidate in ranked:
            if all(np.mean(np.abs(candidate[2] - old[2])) > 2.0 for old in selected):
                selected.append(candidate)
                break
    return selected


def contact_sheet(rows, out):
    sheet = Image.new("RGB", (4 * 240, ((len(rows) + 3) // 4) * 184), "white")
    draw = ImageDraw.Draw(sheet)
    for i, row in enumerate(rows):
        x, y = i % 4 * 240, i // 4 * 184
        with Image.open(out / row["image"]) as im:
            im.thumbnail((230, 150))
            sheet.paste(im, (x, y))
        label = row["image"]
        if "seconds" in row:
            label += f"  {row['seconds']:.2f}s"
        draw.text((x, y + 154), label, fill="black")
    sheet.save(out / "contact-sheet.jpg")


def prepare(args, out):
    register_heif_opener()
    rows = []
    for input_path in args.inputs:
        path = input_path.resolve(strict=True)
        if path.suffix.lower() in {".mp4", ".mov", ".m4v"}:
            with tempfile.TemporaryDirectory(dir=out) as scratch:
                frames = video_candidates(path, Path(scratch), args)
                for frame, time, _, _ in pick(frames, args.limit):
                    name = f"view-{len(rows)+1:03}.jpg"
                    shutil.copyfile(frame, out / name)
                    rows.append(dict(image=name, source=str(path), seconds=time))
        else:
            with Image.open(path) as raw:
                image = ImageOps.exif_transpose(raw).convert("RGB")
                name = f"photo-{len(rows)+1:03}.png"
                image.save(out / name)
            rows.append(dict(image=name, source=str(path)))
    contact_sheet(rows, out)
    (out / "frames.json").write_text(json.dumps(rows, indent=2))
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New evidence directory")
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--fps", type=float, default=2)
    parser.add_argument("--limit", type=int, default=20, help="Max views per clip")
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--end", type=float)
    args = parser.parse_args()
    if not (0 < args.fps <= 30 and 1 <= args.limit <= 100 and args.start >= 0
            and (args.end is None or args.end > args.start)):
        parser.error("Check sample rate, view limit and time interval.")
    if args.output.exists():
        parser.error("Use a new evidence directory to preserve earlier work.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
        out = Path(tmp) / "evidence"
        out.mkdir()
        count = prepare(args, out)
        out.rename(args.output)
    print(f"{count} images: {args.output / 'contact-sheet.jpg'}")
