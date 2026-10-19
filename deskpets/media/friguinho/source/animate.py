"""Build Friguinho's seven desktop-pet cycles from one canonical master image."""
import argparse
import json
import math
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
OUT = parser.parse_args().output
OUT.mkdir(parents=True, exist_ok=True)

MASTER = HERE / "master.png"
STATES = ("idle", "walk", "walk_fast", "run", "swipe", "lie", "drag")
CANVAS = 512
FRAME_COUNT = 8


def components(mask, min_pixels=100):
    """Return connected component point lists from an L-mode mask."""
    width, height = mask.size
    remaining = bytearray(1 if value else 0 for value in mask.tobytes())
    groups = []
    for start, value in enumerate(remaining):
        if not value:
            continue
        remaining[start] = 0
        queue, points = deque([start]), []
        while queue:
            point = queue.popleft()
            points.append(point)
            x, y = point % width, point // width
            for neighbor in (
                point - 1 if x else -1,
                point + 1 if x + 1 < width else -1,
                point - width if y else -1,
                point + width if y + 1 < height else -1,
            ):
                if neighbor >= 0 and remaining[neighbor]:
                    remaining[neighbor] = 0
                    queue.append(neighbor)
        if len(points) >= min_pixels:
            groups.append(points)
    return sorted(groups, key=len, reverse=True)


source = Image.open(MASTER).convert("RGBA")
alpha = source.getchannel("A").point(lambda value: 255 if value >= 96 else 0)
alpha = alpha.filter(ImageFilter.MedianFilter(3))
source.putalpha(alpha)
master_box = alpha.getbbox()
assert master_box, "Canonical Friguinho master has no visible pixels."

# The golden feet are isolated by color only in the lower part of the sprite.
# Their masks are expanded slightly to include the original dark outline.
pixels = source.load()
orange_bytes = bytearray(source.width * source.height)
for y in range(int(source.height * .70), source.height):
    row = y * source.width
    for x in range(source.width):
        r, g, b, a = pixels[x, y]
        if a > 64 and r > 130 and g > 55 and r > g * 1.10 and b < 150:
            orange_bytes[row + x] = 255
orange = Image.frombytes("L", source.size, bytes(orange_bytes))
foot_groups = []
for points in components(orange, min_pixels=1000):
    xs = [point % source.width for point in points]
    ys = [point // source.width for point in points]
    if max(ys) > source.height * .82:
        foot_groups.append((points, (min(xs), min(ys), max(xs) + 1, max(ys) + 1)))
foot_groups.sort(key=lambda item: item[1][0])
assert len(foot_groups) == 2, f"Expected two orange feet; found {len(foot_groups)}."

foot_masks = []
for points, _ in foot_groups:
    raw = bytearray(source.width * source.height)
    for point in points:
        raw[point] = 255
    foot_masks.append(
        Image.frombytes("L", source.size, bytes(raw)).filter(ImageFilter.MaxFilter(15))
    )
feet_mask = ImageChops.lighter(foot_masks[0], foot_masks[1])
body_mask = ImageChops.subtract(alpha, feet_mask)

scale = 430 / (master_box[3] - master_box[1])
offset_x = (CANVAS - (master_box[2] - master_box[0]) * scale) / 2 - master_box[0] * scale
offset_y = (CANVAS - 430) / 2 - master_box[1] * scale
scaled_size = (round(source.width * scale), round(source.height * scale))


def canvas_layer(image, mask=None):
    layer = image.copy()
    if mask is not None:
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    layer = layer.resize(scaled_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (CANVAS, CANVAS))
    canvas.alpha_composite(layer, (round(offset_x), round(offset_y)))
    return canvas


body = canvas_layer(source, body_mask)
feet = [canvas_layer(source, mask) for mask in foot_masks]
foot_centers = []
for _, box in foot_groups:
    left, top, right, _ = box
    foot_centers.append(((left + right) / 2 * scale + offset_x,
                         top * scale + offset_y + 2))


def pose_layer(name):
    """Fit a generated reaction pose to the same canvas and ground baseline."""
    image = Image.open(HERE / "poses" / f"{name}.png").convert("RGBA")
    pose_alpha = image.getchannel("A").point(lambda value: 255 if value >= 96 else 0)
    pose_alpha = pose_alpha.filter(ImageFilter.MedianFilter(3))
    image.putalpha(pose_alpha)
    box = pose_alpha.getbbox()
    assert box, f"Generated {name} pose has no visible pixels."
    crop = image.crop(box)
    ratio = min(430 / crop.height, 454 / crop.width)
    size = (round(crop.width * ratio), round(crop.height * ratio))
    crop = crop.resize(size, Image.Resampling.LANCZOS)
    result = Image.new("RGBA", (CANVAS, CANVAS))
    result.alpha_composite(crop, ((CANVAS - crop.width) // 2, CANVAS - 40 - crop.height))
    return result


special_poses = {name: pose_layer(name) for name in ("swipe", "lie", "drag")}


def transform(layer, pivot, dx=0, dy=0, angle=0, sx=1, sy=1):
    """Apply a stable affine pose transform in the shared 512px registration."""
    theta = math.radians(angle)
    a, b = math.cos(theta) * sx, -math.sin(theta) * sy
    c, d = math.sin(theta) * sx, math.cos(theta) * sy
    px, py = pivot
    tx, ty = px + dx - a * px - b * py, py + dy - c * px - d * py
    determinant = a * d - b * c
    inverse = (
        d / determinant, -b / determinant, (b * ty - d * tx) / determinant,
        -c / determinant, a / determinant, (c * tx - a * ty) / determinant,
    )
    return layer.transform(
        layer.size, Image.Transform.AFFINE, inverse,
        resample=Image.Resampling.BICUBIC,
    )


def build_frame(state, index):
    phase = index * math.tau / FRAME_COUNT
    sine, cosine = math.sin(phase), math.cos(phase)
    moving = state in ("walk", "walk_fast", "run")
    stride, lift, lean = {
        "walk": (16, 12, -1.5),
        "walk_fast": (23, 18, -2.5),
        "run": (31, 25, -4.0),
    }.get(state, (0, 0, 0))
    if state in special_poses:
        pose = special_poses[state]
        if state == "swipe":
            dy = -6.0 * max(0, math.sin(phase * 2))
            angle, sy = 1.5 * sine, 1.0
        elif state == "lie":
            dy, angle, sy = 3.0 * sine + 1.2 * cosine, 0.6 * sine, 1 + 0.008 * sine
        else:
            dy, angle, sy = 4.5 * sine + 2.0 * cosine, 2.5 * sine, 1.0
        frame = transform(pose, (CANVAS / 2, CANVAS * .84), dy=dy,
                          angle=angle, sy=sy).resize((128, 128), Image.Resampling.LANCZOS)
        frame.putalpha(frame.getchannel("A").point(lambda value: 255 if value >= 128 else 0))
        bounds = frame.getchannel("A").getbbox()
        assert bounds and 2 <= bounds[0] < bounds[2] <= 126 and 2 <= bounds[1] < bounds[3] <= 126, (state, index, bounds)
        return frame

    bob = (-1 + 3.2 * sine + 1.4 * cosine) if state == "idle" else -abs(sine) * lift * .65 if moving else 0
    body_angle = lean * sine if moving else 1.3 * sine
    body_sx, body_sy = 1.0, 1.0
    if state == "lie":
        body_sx, body_sy = 1.07, .82
        bob = 20 + 1.2 * sine
        body_angle = 1.0 * sine
    elif state == "drag":
        bob = -2 + 2.0 * cosine
        body_angle = 3.0 * sine
    elif state == "swipe":
        body_angle = 4.0 * math.sin(phase * 2)
        bob = -1.0 + 1.5 * sine

    frame = Image.new("RGBA", (CANVAS, CANVAS))
    for side, (foot, pivot) in enumerate(zip(feet, foot_centers)):
        sign = -1 if side == 0 else 1
        foot_phase = phase + (0 if side else math.pi)
        dx = stride * math.cos(foot_phase)
        dy = -lift * max(0, math.sin(foot_phase))
        angle = -sign * 10 * math.sin(foot_phase) if moving else 0
        if state == "lie":
            dx, dy, angle = sign * 2.5, 0, sign * 7
        elif state == "drag":
            dx = sign * (3 + 2 * sine)
            dy = 10 + sign * 3 * cosine
            angle = sign * (12 + 6 * sine)
        frame.alpha_composite(transform(foot, pivot, dx, dy, angle))

    body_pivot = (CANVAS / 2, CANVAS * .86)
    posed_body = transform(body, body_pivot, dy=bob, angle=body_angle, sx=body_sx, sy=body_sy)
    frame.alpha_composite(posed_body)
    frame = frame.resize((128, 128), Image.Resampling.LANCZOS)
    frame.putalpha(frame.getchannel("A").point(lambda value: 255 if value >= 128 else 0))
    bounds = frame.getchannel("A").getbbox()
    assert bounds and 2 <= bounds[0] < bounds[2] <= 126 and 2 <= bounds[1] < bounds[3] <= 126, (state, index, bounds)
    return frame


cycles = {state: [build_frame(state, index) for index in range(FRAME_COUNT)] for state in STATES}
visible = [pixel[:3] for frames in cycles.values() for frame in frames
           for pixel in frame.get_flattened_data() if pixel[3]]
pool = Image.new("RGB", (len(visible), 1))
pool.putdata(visible)
bank = pool.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
palette = bank.getpalette()[:765] + [255, 0, 255]
bank.putpalette(palette)

manifest = {}
for state, frames in cycles.items():
    indexed_frames = []
    for frame in frames:
        indexed = frame.convert("RGB").quantize(palette=bank, dither=Image.Dither.NONE)
        indexed.putpalette(palette)
        raw = bytearray(indexed.tobytes())
        for point, alpha_value in enumerate(frame.getchannel("A").tobytes()):
            if not alpha_value:
                raw[point] = 255
        indexed.frombytes(bytes(raw))
        indexed.info["transparency"] = 255
        indexed_frames.append(indexed)
    target = OUT / f"blue_{state}_8fps.gif"
    indexed_frames[0].save(
        target,
        save_all=True,
        append_images=indexed_frames[1:],
        loop=0,
        duration=[120, 130] * 4,
        disposal=2,
        transparency=255,
        optimize=False,
    )
    with Image.open(target) as gif:
        assert gif.size == (128, 128) and gif.n_frames == FRAME_COUNT
        for index, expected in enumerate(frames):
            gif.seek(index)
            assert gif.convert("RGBA").getchannel("A").tobytes() == expected.getchannel("A").tobytes()
    manifest[state] = {
        "canvas": [128, 128],
        "frames": FRAME_COUNT,
        "duration_ms": 1000,
        "bboxes": [frame.getchannel("A").getbbox() for frame in frames],
    }

sheet = Image.new("RGB", (1024, len(STATES) * 152), "#f7f9ff")
draw = ImageDraw.Draw(sheet)
for row, state in enumerate(STATES):
    for column, frame in enumerate(cycles[state]):
        sheet.paste(frame, (column * 128, row * 152 + 22), frame)
        draw.text((column * 128 + 4, row * 152 + 4), f"{state} {column + 1}", fill="#1e3157")
sheet.save(OUT / "source" / "all-frames.png")
cycles["idle"][0].save(OUT / "base.png")
(OUT / "source" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print("PASS: Friguinho 7 states, 56 frames, 128x128, transparent loopable GIFs.")
