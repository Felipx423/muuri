"""Project Eco's original texture onto a rounded volume, then animate sideways.

Uses the existing cutout, not independently generated poses. No runtime changes.
Only locomotion GIFs are produced; idle/reaction/rest/drag remain untouched.
"""
import argparse
import json
import math
import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=Path.cwd()/'build/eco-assets')
OUT=parser.parse_args().output
OUT.mkdir(exist_ok=True, parents=True)
MASTER = HERE/'master.png'
SCALE = 432/1099/4
ANGLE = math.radians(65)
C, S = math.cos(ANGLE), math.sin(ANGLE)
STATES = ('walk','walk_fast','run')


def components(mask, width, height):
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
        if len(points) > 100:
            groups.append(points)
    return sorted(groups, key=len, reverse=True)


source = Image.open(MASTER).convert('RGBA')
mask = source.getchannel('A').point(lambda a: 255 if a >= 160 else 0).filter(ImageFilter.MinFilter(3))
parts = {}
groups = components(bytearray(a > 0 for a in mask.tobytes()), *source.size)[:5]
for index, points in enumerate(groups):
    raw = bytearray(source.width*source.height)
    for p in points:
        raw[p] = 255
    image = source.copy()
    image.putalpha(Image.frombytes('L',source.size,bytes(raw)))
    box = image.getchannel('A').getbbox()
    name = 'body' if index == 0 else ('foot_' if box[1]>950 else 'hand_')+('l' if box[0]<627 else 'r')
    parts[name] = image

body = parts['body']
pixels = body.load()
# Sample only the sage rim, never invent a different side material.
rim = {}
for y in range(365,966):
    xs = [x for x in range(274,972) if pixels[x,y][3] >= 128]
    x = min(xs)+min(24,(max(xs)-min(xs))//4) if xs else 620
    rim[y] = pixels[x,y][:3]


def project_body():
    """Orthographic Y rotation of a soft rounded box, textured from the master."""
    factor = SCALE*4
    result = Image.new('RGBA',(320,248))
    target = result.load()
    hx, hy, hz = 348,299,215
    for py in range(result.height):
        y = (py-result.height/2)/factor
        if abs(y) >= hy:
            continue
        y4 = (y/hy)**4
        for px in range(result.width):
            x = (px-result.width/2)/factor
            # Clip the ray to the volume's box, then solve its rounded surface.
            low = max((C*x-hx)/S,(-hz-S*x)/C)
            high = min((C*x+hx)/S,(hz-S*x)/C)
            if low >= high:
                continue
            def surface(t):
                return ((C*x-S*t)/hx)**4 + y4 + ((S*x+C*t)/hz)**4 - 1
            a,b = low,high
            for _ in range(12):
                m1,m2 = (2*a+b)/3,(a+2*b)/3
                if surface(m1) < surface(m2):
                    b = m2
                else:
                    a = m1
            minimum = (a+b)/2
            if surface(minimum) > 0:
                continue
            a,b = minimum,high
            for _ in range(16):
                mid = (a+b)/2
                if surface(mid) <= 0:
                    a = mid
                else:
                    b = mid
            t = (a+b)/2
            ox,oz = C*x-S*t,S*x+C*t
            u,v = round(620.5+ox),max(365,min(965,round(665+y)))
            texture = pixels[u,v]
            # The reference supplies the front texture; the visible flank uses
            # the same row of the original sage rim rather than stretching eyes.
            color = texture[:3] if oz/hz > .70 and texture[3] else rim[v]
            if oz/hz <= .70:
                nx,ny,nz = (ox/hx)**3/hx,(y/hy)**3/hy,(oz/hz)**3/hz
                length = math.sqrt(nx*nx+ny*ny+nz*nz)
                light = max(0,(-.50*nx-.65*ny+.40*nz)/length)
                color = tuple(round(min(255,c*(.91+.19*light))) for c in color)
            target[px,py] = (*color,255)
    return result


def patch(image, box):
    result = Image.new('RGBA', image.size)
    result.paste(image.crop(box),box[:2])
    return result


def texture_piece(name, box=None, sx=1, sy=1, angle=0):
    image = parts[name] if box is None else patch(parts[name],box)
    image = image.crop(image.getchannel('A').getbbox())
    image = image.resize((round(image.width*SCALE*4*sx),round(image.height*SCALE*4*sy)),Image.Resampling.LANCZOS)
    return image.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)


torso = project_body()
stem = texture_piece('body',(548,274,690,370),sx=.75)
leaves = texture_piece('body',(350,70,940,278),sx=.78)
hands = {side:texture_piece('hand_'+side,sx=.92) for side in ('l','r')}
feet = {side:texture_piece('foot_'+side,sx=.94,sy=.88,angle=-32 if side=='l' else 32) for side in ('l','r')}
far = feet['l']
far.putdata([(*tuple(round(c*.82) for c in pixel[:3]),pixel[3]) for pixel in far.getdata()])


def centered(canvas,image,x,y,angle=0,scale=1):
    if scale != 1:
        image=image.resize((round(image.width*scale),round(image.height*scale)),Image.Resampling.LANCZOS)
    if angle:
        image=image.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
    canvas.alpha_composite(image,(round(x*4-image.width/2),round(y*4-image.height/2)))


def body_pose(bob=0,lean=0,leaf_sway=0):
    image=Image.new('RGBA',(512,512))
    centered(image,torso,64,118+(665-1188)*SCALE)
    centered(image,stem,64,118+(322-1188)*SCALE)
    centered(image,leaves,64,118+(182.5-1188)*SCALE,angle=leaf_sway)
    if lean:
        image=image.rotate(lean,resample=Image.Resampling.BICUBIC,center=(256,392))
    result=Image.new('RGBA',image.size)
    result.alpha_composite(image,(0,round(bob*4)))
    return result


def floating_hand(canvas,image,x,y,angle,escape):
    occupied=canvas.getchannel('A').point(lambda a:255 if a>=128 else 0).filter(ImageFilter.MaxFilter(9))
    for step in range(24):
        layer=Image.new('RGBA',canvas.size)
        centered(layer,image,x+escape*step/4,y,angle=angle)
        mask=layer.getchannel('A').point(lambda a:255 if a>=128 else 0)
        if not ImageChops.multiply(occupied,mask).getbbox():
            canvas.alpha_composite(layer)
            return
    raise AssertionError('Hand cannot retain its transparent gap')


all_frames={}
for state in STATES:
    frames=[]
    stride,lift={'walk':(4,2),'walk_fast':(8,3.8),'run':(12,6)}[state]
    for i in range(8):
        t=i*math.tau/8
        # Front-to-back ground phase and back-to-front raised phase, matching
        # the engine's rightward displacement; the engine mirrors this left.
        bob=-lift*.65*abs(math.sin(t))
        lean=-1 if state=='walk' else -2 if state=='walk_fast' else -4
        canvas=body_pose(bob,lean,leaf_sway=1.3*math.sin(t))
        for side,offset,phase in (('l',-3,t+math.pi),('r',3,t)):
            x=64+offset-stride*math.cos(phase)
            y=(110 if side=='l' else 113)-lift*max(0,math.sin(phase))
            centered(canvas,feet[side],x,y,angle=-10*math.sin(phase),scale=.75 if side=='l' else .85)
        # Both floating mittens remain separated from the volume. Their swing
        # follows the opposite foot rather than an outward frontal wave.
        floating_hand(canvas,hands['l'],25.8+1.2*math.sin(t),91.8+bob,-14*math.sin(t),-1)
        floating_hand(canvas,hands['r'],103.0-1.2*math.sin(t),91.8+bob,14*math.sin(t),1)
        frame=canvas.resize((128,128),Image.Resampling.LANCZOS)
        frame.putalpha(frame.getchannel('A').point(lambda a:255 if a>=128 else 0))
        bounds=frame.getchannel('A').getbbox()
        assert bounds and 3<=bounds[0]<bounds[2]<=125 and 3<=bounds[1]<bounds[3]<=125,(state,i,bounds)
        folder=OUT/state
        folder.mkdir(exist_ok=True)
        frame.save(folder/f'frame-{i:02d}.png')
        frames.append(frame)
    all_frames[state]=frames

visible=[pixel[:3] for frames in all_frames.values() for frame in frames for pixel in frame.getdata() if pixel[3]]
pool=Image.new('RGB',(len(visible),1))
pool.putdata(visible)
bank=pool.quantize(colors=255,method=Image.Quantize.MEDIANCUT)
palette=bank.getpalette()[:765]+[255,0,255]
bank.putpalette(palette)
manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8')) if (OUT/'manifest.json').exists() else {}
for state,frames in all_frames.items():
    indexed_frames=[]
    for frame in frames:
        indexed=frame.convert('RGB').quantize(palette=bank,dither=Image.Dither.NONE)
        indexed.putpalette(palette)
        raw=bytearray(indexed.tobytes())
        for p,a in enumerate(frame.getchannel('A').tobytes()):
            if not a:raw[p]=255
            else:assert raw[p]!=255
        indexed.frombytes(bytes(raw))
        indexed.info['transparency']=255
        indexed_frames.append(indexed)
    target=OUT/f'green_{state}_8fps.gif'
    indexed_frames[0].save(target,save_all=True,append_images=indexed_frames[1:],loop=0,duration=[120,130]*4,disposal=2,transparency=255,optimize=False)
    with Image.open(target) as gif:
        assert gif.n_frames==8
        for i,frame in enumerate(frames):
            gif.seek(i)
            assert gif.convert('RGBA').getchannel('A').tobytes()==frame.getchannel('A').tobytes()
    manifest[state]=dict(canvas=[128,128],frames=8,duration_ms=1000,
                         direction='right',view='side',bboxes=[f.getchannel('A').getbbox() for f in frames])
contact=Image.new('RGB',(1024,152*3),'#f8faff')
draw=ImageDraw.Draw(contact)
for y in range(0,contact.height,8):
    for x in range(0,1024,8):
        if (x//8+y//8)%2:draw.rectangle((x,y,x+7,y+7),fill='#dce6f2')
for row,(state,frames) in enumerate(all_frames.items()):
    for col,frame in enumerate(frames):
        contact.paste(frame,(col*128,row*152+24),frame)
        draw.text((col*128+4,row*152+4),f'{state} {col+1}',fill='#223957')
contact.save(OUT/'frames-laterais.png')
body_pose().resize((128,128),Image.Resampling.LANCZOS).save(OUT/'corpo-perfil.png')
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('PASS three sideways cycles, same master texture, 128px/8 frames, exact alpha roundtrip.')

# Refresh the complete contact sheet when invoked after the frontal builder.
names=('idle','walk','walk_fast','run','swipe','lie','drag')
if all((OUT/name/'frame-00.png').exists() for name in names):
    contact=Image.new('RGB',(1024,152*7),'#f8faff')
    draw=ImageDraw.Draw(contact)
    for y in range(0,contact.height,8):
        for x in range(0,1024,8):
            if (x//8+y//8)%2:draw.rectangle((x,y,x+7,y+7),fill='#dce6f2')
    for row,name in enumerate(names):
        for col in range(8):
            frame=Image.open(OUT/name/f'frame-{col:02d}.png').convert('RGBA')
            contact.paste(frame,(col*128,row*152+24),frame)
            draw.text((col*128+4,row*152+4),f'{name} {col+1}',fill='#223957')
    contact.save(OUT/'todos-os-frames.png')
