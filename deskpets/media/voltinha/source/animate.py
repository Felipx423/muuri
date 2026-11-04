"""Build Voltinha's seven 128 px desktop-pet cycles from one canonical master."""
import json
import math
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


HERE = Path(__file__).resolve().parent
OUT = HERE.parent
MASTER = HERE / "master.png"
STATES = ("idle", "walk", "walk_fast", "run", "swipe", "lie", "drag")
CANVAS = 512


def components(mask):
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
        if len(points) > 500:
            groups.append(points)
    return sorted(groups, key=len, reverse=True)


source = Image.open(MASTER).convert("RGBA")
alpha = source.getchannel("A").point(lambda value: 255 if value >= 96 else 0)
alpha = alpha.filter(ImageFilter.MedianFilter(3))
source.putalpha(alpha)
master_box = alpha.getbbox()
assert master_box
scale = 464 / (master_box[3] - master_box[1])
offset_x = (CANVAS - (master_box[2] - master_box[0]) * scale) / 2
offset_y = 18

parts = {}
for index, points in enumerate(components(alpha)[:5]):
    raw = bytearray(source.width * source.height)
    for point in points:
        raw[point] = 255
    isolated = source.copy()
    isolated.putalpha(Image.frombytes("L", source.size, bytes(raw)))
    box = isolated.getchannel("A").getbbox()
    crop = isolated.crop(box)
    crop = crop.resize(
        (max(1, round(crop.width * scale)), max(1, round(crop.height * scale))),
        Image.Resampling.LANCZOS,
    )
    crop.putalpha(crop.getchannel("A").point(lambda value: 255 if value >= 128 else 0))
    center = (
        offset_x + ((box[0] + box[2]) / 2 - master_box[0]) * scale,
        offset_y + ((box[1] + box[3]) / 2 - master_box[1]) * scale,
    )
    if index == 0:
        name = "body"
    elif center[1] > 400:
        name = "foot_l" if center[0] < CANVAS / 2 else "foot_r"
    else:
        name = "hand_l" if center[0] < CANVAS / 2 else "hand_r"
    parts[name] = (crop, center)

assert set(parts) == {"body", "hand_l", "hand_r", "foot_l", "foot_r"}, set(parts)


def place(canvas, name, dx=0, dy=0, angle=0, sx=1, sy=1, center=None):
    image, default_center = parts[name]
    target_center = center or default_center
    if sx != 1 or sy != 1:
        image = image.resize(
            (max(1, round(image.width * sx)), max(1, round(image.height * sy))),
            Image.Resampling.LANCZOS,
        )
    if angle:
        image = image.rotate(angle, Image.Resampling.BICUBIC, expand=True)
    x = round(target_center[0] + dx - image.width / 2)
    y = round(target_center[1] + dy - image.height / 2)
    canvas.alpha_composite(image, (x, y))


def build_frame(state, index):
    phase = index * math.tau / 8
    sine, cosine = math.sin(phase), math.cos(phase)
    canvas = Image.new("RGBA", (CANVAS, CANVAS))
    moving = state in ("walk", "walk_fast", "run")
    stride, lift, lean = {
        "walk": (13, 8, -2.5),
        "walk_fast": (22, 13, -4.5),
        "run": (30, 19, -7.0),
    }.get(state, (0, 0, 0))
    bob = -abs(sine) * (5 if moving else 2)
    idle_motion = sine + .37 * cosine
    if state == "idle":
        bob = -1 + 2 * idle_motion

    if state == "lie":
        rest = sine + .35 * cosine
        place(canvas, "body", dx=2, dy=25 + rest, angle=76 + rest, sx=.72, sy=.72, center=(250, 272))
        place(canvas, "hand_l", dx=-12, dy=8 + rest, angle=-35 - rest, center=(114, 365))
        place(canvas, "hand_r", dx=8, dy=rest, angle=28 + rest, center=(390, 360))
        place(canvas, "foot_l", dx=24, dy=-6 + rest, angle=66 + rest, center=(195, 428))
        place(canvas, "foot_r", dx=-12, dy=-2 - rest, angle=45 - rest, center=(338, 430))
    else:
        body_angle = lean + (1.2 * idle_motion if state == "idle" else 1.2 * sine if state == "drag" else 0)
        body_sx = .96 if moving else 1
        body_sy = 1.01 if moving else 1 + .006 * sine
        if state == "drag":
            body_angle = 4 * sine
            bob = -5 + 3 * cosine
        place(canvas, "body", dy=bob, angle=body_angle, sx=body_sx, sy=body_sy)

        for side, sign in (("l", -1), ("r", 1)):
            foot_phase = phase + (0 if side == "r" else math.pi)
            foot_dx = stride * math.cos(foot_phase)
            foot_dy = -lift * max(0, math.sin(foot_phase))
            foot_angle = -sign * 10 * math.sin(foot_phase)
            if state == "drag":
                foot_dx = sign * 8 + sign * 4 * sine
                foot_dy = 18 + sign * 5 * cosine
                foot_angle = sign * (18 + 8 * sine)
            place(canvas, f"foot_{side}", dx=foot_dx, dy=foot_dy, angle=foot_angle)

        for side, sign in (("l", -1), ("r", 1)):
            hand_dx = -sign * stride * .22 * cosine if moving else sign * 2 * sine
            hand_dy = bob + (sign * 5 * sine if moving else 0)
            hand_angle = sign * 13 * sine if moving else sign * 3 * sine
            if state == "swipe" and side == "r":
                lift_hand = (1 - cosine) / 2
                hand_dx = -22 * lift_hand
                hand_dy = -88 * lift_hand
                hand_angle = -55 * lift_hand
            elif state == "drag":
                hand_dx = sign * 7 + sign * 3 * sine
                hand_dy = 30 + sign * 6 * cosine
                hand_angle = sign * (24 + 8 * sine)
            place(canvas, f"hand_{side}", dx=hand_dx, dy=hand_dy, angle=hand_angle)

    frame = canvas.resize((128, 128), Image.Resampling.LANCZOS)
    frame.putalpha(frame.getchannel("A").point(lambda value: 255 if value >= 128 else 0))
    bounds = frame.getchannel("A").getbbox()
    assert bounds and 2 <= bounds[0] < bounds[2] <= 126 and 2 <= bounds[1] < bounds[3] <= 126, (state, index, bounds)
    return frame


cycles = {state: [build_frame(state, index) for index in range(8)] for state in STATES}

# A common palette prevents color flicker between frames and states.
pixels = [pixel[:3] for frames in cycles.values() for frame in frames for pixel in frame.getdata() if pixel[3]]
pool = Image.new("RGB", (len(pixels), 1))
pool.putdata(pixels)
palette_image = pool.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
palette = palette_image.getpalette()[:765] + [255, 0, 255]
palette_image.putpalette(palette)

manifest = {}
for state, frames in cycles.items():
    indexed_frames = []
    for frame in frames:
        indexed = frame.convert("RGB").quantize(palette=palette_image, dither=Image.Dither.NONE)
        indexed.putpalette(palette)
        raw = bytearray(indexed.tobytes())
        for position, visible in enumerate(frame.getchannel("A").tobytes()):
            if not visible:
                raw[position] = 255
            else:
                assert raw[position] != 255
        indexed.frombytes(bytes(raw))
        indexed.info["transparency"] = 255
        indexed_frames.append(indexed)
    target = OUT / f"green_{state}_8fps.gif"
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
        assert gif.n_frames == 8, (state, gif.n_frames)
        for index, frame in enumerate(frames):
            gif.seek(index)
            assert gif.convert("RGBA").getchannel("A").tobytes() == frame.getchannel("A").tobytes()
    manifest[state] = {
        "canvas": [128, 128],
        "frames": 8,
        "duration_ms": 1000,
        "view": "rightward lean" if state in ("walk", "walk_fast", "run") else "front",
        "bboxes": [frame.getchannel("A").getbbox() for frame in frames],
    }

sheet = Image.new("RGB", (1024, 1064), "#f8faff")
draw = ImageDraw.Draw(sheet)
for y in range(0, sheet.height, 8):
    for x in range(0, sheet.width, 8):
        if (x // 8 + y // 8) % 2:
            draw.rectangle((x, y, x + 7, y + 7), fill="#dce6f2")
for row, state in enumerate(STATES):
    for column, frame in enumerate(cycles[state]):
        sheet.paste(frame, (column * 128, row * 152 + 24), frame)
        draw.text((column * 128 + 4, row * 152 + 4), f"{state} {column + 1}", fill="#223957")
sheet.save(OUT / "source" / "todos-os-frames.png")
cycles["idle"][0].save(OUT / "base.png")
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print("PASS: Voltinha 7 states, 56 frames, 128x128, shared master and exact alpha roundtrip.")
