"""Prepare clean sources anywhere; build/sign an arm64 .app only on a Mac."""
import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT/'build/macos'
OUTPUT = ROOT/'dist/macos'


def clean_defaults():
    catalog = json.loads((ROOT/'deskpets/pets_data.json').read_text(encoding='utf-8'))
    entries = []
    for species, data in catalog.items():
        color = data['colors'][0]
        interactive = 'drag' in data['states'][color]
        entries.append(dict(species=species,colors=[color],enabled=species=='muuri',
                            size='Medium' if species=='muuri' else 'Original',count=1,
                            draggable=interactive,settings_clicks=4 if interactive else 0,
                            physics_enabled=False,movement_multiplier=1.,animation_multiplier=1.))
    return {'pets':entries}


def source_files():
    excluded = {'.git','.venv','__pycache__','.idea','.vscode','build','dist',
                '.pytest_cache','.mypy_cache','.ruff_cache','htmlcov'}
    for path in sorted(ROOT.rglob('*')):
        rel = path.relative_to(ROOT)
        if any(p in excluded or p.endswith('.egg-info') for p in rel.parts):
            continue
        if path.is_file() and not (path.name.startswith('.env') or path.suffix in {'.pyc','.log','.p12','.pfx','.key'}):
            yield path, rel


def prepare():
    WORK.mkdir(parents=True,exist_ok=True)
    OUTPUT.mkdir(parents=True,exist_ok=True)
    defaults = WORK/'defaults'
    defaults.mkdir(exist_ok=True)
    prefs = json.dumps(clean_defaults(),ensure_ascii=False,indent=4)+'\n'
    (defaults/'pets_list.json').write_text(prefs,encoding='utf-8')
    (defaults/'config.json').write_text('{"layer":"front"}\n',encoding='utf-8')
    replacements = {'deskpets/pets_list.json':prefs.encode('utf-8'),
                    'deskpets/config.json':b'{"layer":"front"}\n'}
    source = OUTPUT/'Muuri-macOS-codigo-fonte.zip'
    embedded = WORK/'Muuri-codigo-fonte.zip'
    with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED) as full, \
            zipfile.ZipFile(embedded,'w',zipfile.ZIP_DEFLATED) as small:
        for path,rel in source_files():
            name = rel.as_posix()
            content = replacements.get(name,path.read_bytes())
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if path.suffix=='.command' else 0o100644) << 16
            full.writestr(info,content)
            if not name.startswith(('deskpets/media/','img/')):
                small.writestr(copy.copy(info),content)
        small.writestr('ASSETS-DO-FONTE.txt',
                       'Copie a pasta deskpets/media do diretório Resources de Muuri.app\n'
                       'para deskpets/media no fonte extraído. O ZIP autônomo inclui todos os assets.\n')
    icon = WORK/'Muuri.icns'
    with Image.open(ROOT/'deskpets/media/muuri/muuri.ico') as image:
        image.convert('RGBA').save(icon,format='ICNS')
    shutil.copy2(ROOT/'packaging/MACOS.md',OUTPUT/'COMO-USAR-NO-MAC.md')
    write_hashes()
    return defaults,source,embedded,icon


def licenses():
    folder = WORK/'THIRD_PARTY_LICENSES'
    folder.mkdir(exist_ok=True)
    for name in ('PyQt6','PyQt6-Qt6','PyQt6-sip','Pillow','pyinstaller','pyobjc-core','pyobjc-framework-Cocoa'):
        dist = importlib.metadata.distribution(name)
        for file in dist.files or []:
            if '.dist-info/' in str(file) and any(word in str(file).lower() for word in ('license','copying','notice')):
                path = Path(dist.locate_file(file))
                if path.is_file():
                    target = folder/name/Path(*file.parts[1:])
                    target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(path,target)
    return folder


def verify(app):
    info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
    if not info.get('LSUIElement') or info['LSMinimumSystemVersion'] != '13.0':
        raise RuntimeError('Metadados do aplicativo incorretos')
    executable = app/'Contents/MacOS/Muuri'
    subprocess.run(['lipo',str(executable),'-verify_arch','arm64'],check=True)
    subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)
    resource = app/'Contents/Resources'
    for relative in ('LICENSE','THIRD_PARTY_LICENSES','Muuri-codigo-fonte.zip','deskpets/pets_data.json'):
        if not (resource/relative).exists():
            raise RuntimeError(f'Recurso ausente: {relative}')
    prefs = json.loads((resource/'deskpets/pets_list.json').read_text(encoding='utf-8'))
    if prefs != clean_defaults():
        raise RuntimeError('Preferências pessoais entraram no pacote')
    seen = set()
    required = (13,0)
    for path in app.rglob('*'):
        if not path.is_file() or path.resolve() in seen:
            continue
        seen.add(path.resolve())
        with path.open('rb') as handle:
            magic = handle.read(4)
        if magic not in (b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca'):
            continue
        subprocess.run(['lipo',str(path),'-verify_arch','arm64'],check=True,capture_output=True)
        loads = subprocess.check_output(['otool','-l',str(path)],text=True)
        versions = re.findall(r'\bminos\s+(\d+\.\d+(?:\.\d+)?)',loads)
        versions += re.findall(r'cmd LC_VERSION_MIN_MACOSX\s+cmdsize \d+\s+version (\d+\.\d+(?:\.\d+)?)',loads)
        for value in versions:
            version = tuple(int(p) for p in value.split('.')[:2])
            if version > required:
                raise RuntimeError(f'{path.name} exige macOS {value}; não é compatível com o alvo 13.0')
    for asset in (ROOT/'deskpets/media').rglob('*'):
        if asset.is_file():
            packaged = resource/'deskpets/media'/asset.relative_to(ROOT/'deskpets/media')
            if not packaged.exists() or hashlib.sha256(asset.read_bytes()).digest()!=hashlib.sha256(packaged.read_bytes()).digest():
                raise RuntimeError(f'Asset alterado/ausente: {asset.name}')
    print('Pacote verificado: arm64, assinatura, alvo macOS 13, fontes/licenças, defaults e assets.')


def write_hashes():
    names = ('Muuri-macOS-arm64-teste.zip','Muuri-macOS-arm64-teste.dmg',
             'Muuri-macOS-codigo-fonte.zip','COMO-USAR-NO-MAC.md')
    lines = [hashlib.sha256((OUTPUT/name).read_bytes()).hexdigest()+'  '+name for name in names if (OUTPUT/name).exists()]
    (OUTPUT/'MUURI-macOS-SHA256.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def build(args):
    if not args.prepare_only and (sys.platform!='darwin' or platform.machine()!='arm64'):
        raise RuntimeError('O .app precisa ser compilado em um Mac com Python arm64. Use --prepare-only para preparar os fontes aqui.')
    defaults,source,embedded,icon = prepare()
    if args.prepare_only:
        print('Fontes preparados, sem binário .app:',source)
        return
    args_list = [sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed',
                 '--onedir','--name','Muuri','--target-architecture','arm64',
                 '--osx-bundle-identifier','io.github.felipx423.muuri','--icon',str(icon),
                 '--distpath',str(WORK/'dist'),'--workpath',str(WORK/'build'),
                 '--specpath',str(WORK),'--additional-hooks-dir',str(ROOT/'packaging/hooks'),
                 '--collect-submodules','AppKit','--collect-submodules','Foundation',
                 '--collect-submodules','objc','--collect-data','AppKit','--collect-data','Foundation',
                 '--exclude-module','deskpets.windows_API','--exclude-module','win32gui',
                 '--exclude-module','win32con','--exclude-module','PyQt6.QtWebEngineWidgets',
                 '--exclude-module','PyQt6.QtWebEngineCore','--exclude-module','PIL.AvifImagePlugin']
    if args.codesign_identity:
        args_list += ['--codesign-identity',args.codesign_identity]
    for path,target in ((ROOT/'deskpets/media','deskpets/media'),(ROOT/'deskpets/pets_data.json','deskpets'),
                        (defaults/'pets_list.json','deskpets'),(defaults/'config.json','deskpets'),
                        (ROOT/'LICENSE','.'),(ROOT/'README.md','.'),(ROOT/'packaging/MACOS.md','.'),
                        (licenses(),'THIRD_PARTY_LICENSES'),(embedded,'.')):
        args_list += ['--add-data',f'{path}:{target}']
    args_list.append(str(ROOT/'run.py'))
    env = os.environ.copy()
    env['MACOSX_DEPLOYMENT_TARGET']='13.0'
    subprocess.run(args_list,cwd=ROOT,env=env,check=True)
    app = WORK/'dist/Muuri.app'
    plist_path = app/'Contents/Info.plist'
    info = plistlib.loads(plist_path.read_bytes())
    version = re.search(r'^AppVersion=(.+)$',(ROOT/'packaging/muuri.iss').read_text(),re.M).group(1).strip()
    info.update(LSUIElement=True,LSMinimumSystemVersion='13.0',CFBundleShortVersionString=version,
                CFBundleVersion=version,NSHighResolutionCapable=True,CFBundleAllowMixedLocalizations=True)
    plist_path.write_bytes(plistlib.dumps(info))
    command = ['codesign','--force','--sign',args.codesign_identity or '-']
    if args.codesign_identity:
        command += ['--options','runtime','--timestamp']
    subprocess.run([*command,str(app)],check=True)
    verify(app)
    subprocess.run([sys.executable,str(ROOT/'packaging/smoke_macos.py'),str(app)],check=True)
    archive = OUTPUT/'Muuri-macOS-arm64-teste.zip'
    subprocess.run(['ditto','-c','-k','--sequesterRsrc','--keepParent',str(app),str(archive)],check=True)
    if args.dmg:
        with tempfile.TemporaryDirectory(prefix='dmg-',dir=WORK) as folder:
            staging = Path(folder)
            subprocess.run(['ditto',str(app),str(staging/'Muuri.app')],check=True)
            (staging/'Applications').symlink_to('/Applications',target_is_directory=True)
            subprocess.run(['hdiutil','create','-ov','-volname','Muuri','-srcfolder',str(staging),
                            '-format','UDZO',str(OUTPUT/'Muuri-macOS-arm64-teste.dmg')],check=True)
    write_hashes()
    print('Aplicativo:',app)
    print('Pacotes:',OUTPUT)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--dmg',action='store_true')
    parser.add_argument('--codesign-identity',default=os.environ.get('MUURI_CODESIGN_IDENTITY'))
    build(parser.parse_args())
