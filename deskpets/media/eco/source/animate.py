"""Animate the same Eco cutout; no frame-by-frame character generation.

The user explicitly approved moving the existing leaves, hands and feet after
the image service could not produce the remaining atlases. Pillow only, with
one shared 128px registration and one palette across all seven GIFs.
"""
import argparse
import json
import math
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=Path.cwd()/'build/eco-assets')
OUT = parser.parse_args().output
OUT.mkdir(exist_ok=True, parents=True)
STATES = ('idle', 'walk', 'walk_fast', 'run', 'swipe', 'lie', 'drag')
FACTOR = 432 / 1099


def components(mask, width, height, minimum=8):
    groups = []
    for start in range(len(mask)):
        if not mask[start]:
            continue
        mask[start] = 0
        queue, points = deque([start]), []
        while queue:
            p = queue.popleft()
            points.append(p)
            x, y = p % width, p // width
            for n in (p-1 if x else -1, p+1 if x+1 < width else -1,
                      p-width if y else -1, p+width if y+1 < height else -1):
                if n >= 0 and mask[n]:
                    mask[n] = 0
                    queue.append(n)
        if len(points) >= minimum:
            groups.append(points)
    return sorted(groups, key=len, reverse=True)


source = Image.open(HERE/'master.png').convert('RGBA')
alpha = source.getchannel('A').point(lambda a: 255 if a >= 160 else 0)
# Remove subpixel matte speckles before reducing the 1254px master to 128px.
alpha = alpha.filter(ImageFilter.MinFilter(3))
groups = components(bytearray(a > 0 for a in alpha.tobytes()), *source.size)[:5]
assert len(groups) == 5 and min(map(len, groups)) > 20000
parts = {}
for points in groups:
    raw = bytearray(source.width*source.height)
    for p in points:
        raw[p] = 255
    mask = Image.frombytes('L', source.size, bytes(raw))
    image = source.copy()
    image.putalpha(mask)
    box = mask.getbbox()
    if len(points) == len(groups[0]):
        name = 'body'
    elif box[1] > 950:
        name = 'foot_l' if box[0] < source.width/2 else 'foot_r'
    else:
        name = 'hand_l' if box[0] < source.width/2 else 'hand_r'
    parts[name] = image

# Detach only the existing green leaves from the stem; retain their own shading.
body = parts['body']
body_bytes = bytearray(body.getchannel('A').tobytes())
for side in ('l', 'r'):
    raw = bytearray(source.width*source.height)
    for p, (r, g, b, a) in enumerate(body.getdata()):
        x, y = p % source.width, p // source.width
        if a and y < 310 and g > r*1.045 and g > b*1.08 and ((x < 632) == (side == 'l')):
            raw[p] = 255
            body_bytes[p] = 0
    leaf = source.copy()
    leaf.putalpha(Image.frombytes('L', source.size, bytes(raw)))
    assert leaf.getbbox()
    parts['leaf_'+side] = leaf
body.putalpha(Image.frombytes('L', source.size, bytes(body_bytes)))


def eyelids(image, openness):
    """Compress the original blue eyes over a locally interpolated face patch."""
    if openness >= .999:
        return image
    result = image.copy()
    for box in ((454, 545, 566, 749), (667, 545, 782, 749)):
        left, top, right, bottom = box
        eye = image.crop(box)
        mask = Image.new('L', eye.size)
        mask.putdata([255 if a and b > r*1.18 and b > g*1.04 else 0
                      for r, g, b, a in eye.getdata()])
        mask = mask.filter(ImageFilter.MaxFilter(7))
        eye.putalpha(mask)
        # Interpolate the same face's colors on either side of each eye.
        for y in range(top, bottom):
            c1, c2 = image.getpixel((left-4, y)), image.getpixel((right+4, y))
            for x in range(left, right):
                t = (x-left)/(right-left-1)
                result.putpixel((x, y), tuple(round(c1[k]*(1-t)+c2[k]*t) for k in range(4)))
        eye = eye.resize((eye.width, max(12, round(eye.height*openness))), Image.Resampling.LANCZOS)
        result.alpha_composite(eye, (left, round((top+bottom-eye.height)/2)))
    return result


def place(canvas, image, pivot=None, dx=0, dy=0, angle=0, sx=1, sy=1):
    box = image.getchannel('A').getbbox()
    crop = image.crop(box)
    px, py = pivot or ((box[0]+box[2])/2, (box[1]+box[3])/2)
    theta = math.radians(angle)
    a, b = math.cos(theta)*FACTOR*sx, -math.sin(theta)*FACTOR*sy
    c, d = math.sin(theta)*FACTOR*sx, math.cos(theta)*FACTOR*sy
    tx = (px-620.5)*FACTOR+256+dx*4 + a*(box[0]-px)+b*(box[1]-py)
    ty = (py-1188)*FACTOR+472+dy*4 + c*(box[0]-px)+d*(box[1]-py)
    det = a*d-b*c
    inverse = (d/det, -b/det, (b*ty-d*tx)/det,
               -c/det, a/det, (c*tx-a*ty)/det)
    canvas.alpha_composite(crop.transform(canvas.size, Image.Transform.AFFINE, inverse,
                                         resample=Image.Resampling.BICUBIC))


def floating_part(canvas, image, escape, **pose):
    """Keep the reference's visible air gap around each detached hand/foot."""
    occupied = canvas.getchannel('A').point(lambda a: 255 if a >= 128 else 0)
    occupied = occupied.filter(ImageFilter.MaxFilter(9))
    for step in range(40):
        layer = Image.new('RGBA', canvas.size)
        adjusted = dict(pose)
        adjusted['dx'] = pose.get('dx', 0)+escape[0]*step/4
        adjusted['dy'] = pose.get('dy', 0)+escape[1]*step/4
        place(layer, image, **adjusted)
        mask = layer.getchannel('A').point(lambda a: 255 if a >= 128 else 0)
        if not ImageChops.multiply(occupied, mask).getbbox():
            canvas.alpha_composite(layer)
            return
    raise AssertionError('Floating part cannot keep its air gap')


all_frames = {}
for state in STATES:
    frames = []
    for index in range(8):
        t = index*math.tau/8
        sine, cosine = math.sin(t), math.cos(t)
        moving = state in ('walk', 'walk_fast', 'run')
        stride = {'walk': 2, 'walk_fast': 3, 'run': 4.4}.get(state, 0)
        lift = {'walk': 2.4, 'walk_fast': 4, 'run': 5.8}.get(state, 0)
        bob = -(0.65 if state == 'idle' else 1.2 if moving else .5)*(1-math.cos(2*t))/2
        if moving:
            bob = -lift*.75*abs(sine)
        tilt = (1.0 if moving else .3)*sine
        if state == 'drag':
            bob, tilt = -4+1.3*sine, 2.5*sine
        openness = (.08 if index == 5 else .45 if index == 6 else 1) if state == 'idle' else 1
        if state == 'lie':
            openness = .10 + .025*(1+cosine)
        canvas = Image.new('RGBA', (512,512))
        b = eyelids(body, openness)
        resting = state == 'lie'
        body_sx, body_sy = (1.018, .90) if resting else (1, 1)
        place(canvas, b, pivot=(620.5,965), dy=bob, angle=tilt,
              sx=body_sx, sy=body_sy)
        theta = math.radians(tilt)
        hinge_x, hinge_y = (632-620.5)*body_sx, (261-965)*body_sy
        hinge_dx = (hinge_x*math.cos(theta)-hinge_y*math.sin(theta)-(632-620.5))*FACTOR/4
        hinge_dy = (hinge_x*math.sin(theta)+hinge_y*math.cos(theta)-(261-965))*FACTOR/4
        for side, sign in (('l', 1), ('r', -1)):
            # Follow the body's stem transform before adding a local leaf sway.
            place(canvas, parts['leaf_'+side], pivot=(632,261),
                  dx=hinge_dx, dy=bob+hinge_dy+.15,
                  angle=tilt+sign*(2 if not moving else 3)*sine + (-sign*5 if resting else 0))
        # Feet retain their exact original shape and volume; opposite half-cycles.
        for side, sign in (('l', 1), ('r', -1)):
            step = sine*sign
            dx, dy = stride*cosine*sign, -lift*max(0, step)
            angle = 10*step if moving else 0
            if state == 'lie':
                dx, dy, angle = -sign*1.8, 0, sign*13
            elif state == 'drag':
                dx, dy, angle = 1.2*sine*sign, bob+3+cosine*sign, 12*sine*sign
            floating_part(canvas, parts['foot_'+side], (0,1), dx=dx, dy=dy, angle=angle)
        for side, sign in (('l', 1), ('r', -1)):
            dx, dy, angle = 0, bob, -sign*10*sine if moving else sign*sine
            if moving:
                dy += sign*1.6*sine
            elif state == 'swipe' and side == 'r':
                raise_hand = (1-cosine)/2
                dx, dy, angle = 1.5*raise_hand, bob-13*raise_hand, -30*raise_hand+8*math.sin(2*t)*raise_hand
            elif resting:
                dx, dy, angle = sign*2, 3+.3*sine, -sign*10
            elif state == 'drag':
                dx, dy, angle = sign*.8*sine, bob-6, sign*18+6*sine
            floating_part(canvas, parts['hand_'+side], (-sign,0), dx=dx, dy=dy, angle=angle)
        frame = canvas.resize((128,128), Image.Resampling.LANCZOS)
        frame.putalpha(frame.getchannel('A').point(lambda a: 255 if a >= 128 else 0))
        box = frame.getchannel('A').getbbox()
        assert box and 3 <= box[0] < box[2] <= 125 and 3 <= box[1] < box[3] <= 125, (state,index,box)
        frames.append(frame)
    all_frames[state] = frames

# One palette for every state keeps colors stable; index 255 is transparency.
visible = [pixel[:3] for frames in all_frames.values() for frame in frames
           for pixel in frame.getdata() if pixel[3]]
pool = Image.new('RGB', (len(visible),1))
pool.putdata(visible)
bank = pool.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
palette = bank.getpalette()[:765] + [255,0,255]
bank.putpalette(palette)
manifest = {}
for state, frames in all_frames.items():
    indexed_frames = []
    for i, frame in enumerate(frames):
        folder = OUT/state
        folder.mkdir(exist_ok=True)
        frame.save(folder/f'frame-{i:02d}.png')
        indexed = frame.convert('RGB').quantize(palette=bank, dither=Image.Dither.NONE)
        indexed.putpalette(palette)
        raw = bytearray(indexed.tobytes())
        for p, a in enumerate(frame.getchannel('A').tobytes()):
            if not a:
                raw[p] = 255
            else:
                assert raw[p] != 255
        indexed.frombytes(bytes(raw))
        indexed.info['transparency'] = 255
        indexed_frames.append(indexed)
    target = OUT/f'green_{state}_8fps.gif'
    indexed_frames[0].save(target, save_all=True, append_images=indexed_frames[1:],
                          loop=0, duration=[120,130]*4, disposal=2, transparency=255, optimize=False)
    with Image.open(target) as gif:
        assert gif.n_frames == 8, (state,gif.n_frames)
        for i, frame in enumerate(frames):
            gif.seek(i)
            assert gif.convert('RGBA').getchannel('A').tobytes() == frame.getchannel('A').tobytes()
    manifest[state] = dict(canvas=[128,128], frames=8, duration_ms=1000,
                           bboxes=[frame.getchannel('A').getbbox() for frame in frames])

contact = Image.new('RGB',(1024,7*152),'#f8faff')
draw = ImageDraw.Draw(contact)
for y in range(0,contact.height,8):
    for x in range(0,contact.width,8):
        if (x//8+y//8)%2:
            draw.rectangle((x,y,x+7,y+7),fill='#dce6f2')
for row,(state,frames) in enumerate(all_frames.items()):
    for col,frame in enumerate(frames):
        contact.paste(frame,(col*128,row*152+24),frame)
        draw.text((col*128+4,row*152+4),f'{state} {col+1}',fill='#223957')
contact.save(OUT/'todos-os-frames.png')
all_frames['idle'][0].save(OUT/'base-128.png')
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
# Override locomotion with the same master viewed from the side.
import subprocess
import sys
subprocess.run([sys.executable,str(HERE/'sideways.py'),'--output',str(OUT)],check=True)
print('PASS: 7 states, 56 frames, 128x128, sideways locomotion, exact alpha roundtrip, safe margins.')
