from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import zipfile
import importlib.metadata

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent / 'work' / 'package'
OUTPUT = ROOT.parents[1] / 'outputs'

def build():
    WORK.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    defaults = WORK / 'defaults'
    defaults.mkdir(exist_ok=True)
    data = json.loads((ROOT / 'deskpets/pets_list.json').read_text(encoding='utf-8'))
    for pet in data['pets']:
        pet['enabled'] = pet['species'] == 'muuri'
        if pet['species'] == 'muuri':
            pet.update(colors=['blue'], size='Medium', draggable=True, settings_clicks=4,
                       movement_multiplier=1.0, animation_multiplier=1.0, physics_enabled=False)
    (defaults / 'pets_list.json').write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding='utf-8')
    (defaults / 'config.json').write_text('{"layer": "front"}\n', encoding='utf-8')
    licenses = WORK / 'THIRD_PARTY_LICENSES'
    licenses.mkdir(exist_ok=True)
    for name in ('PyQt6', 'PyQt6-Qt6', 'PyQt6-sip', 'Pillow', 'pywin32', 'pyinstaller'):
        dist = importlib.metadata.distribution(name)
        for file in dist.files or []:
            if '.dist-info/' in str(file) and any(word in str(file).lower() for word in ('license', 'copying', 'notice')):
                src = Path(dist.locate_file(file))
                target = licenses / name / Path(*file.parts[1:])
                target.parent.mkdir(parents=True, exist_ok=True)
                if src.is_file():
                    shutil.copy2(src, target)
    source = WORK / 'Muuri-codigo-fonte.zip'
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in ROOT.rglob('*'):
            rel = path.relative_to(ROOT)
            if any(part in ('.git', '.venv', '__pycache__', '.idea') or part.endswith('.egg-info') for part in rel.parts):
                continue
            if path.is_file():
                archive.write(path, rel.as_posix())
    # Assets already ship unchanged next to this archive. Keep them once in the
    # installer, and provide the complete standalone source archive separately.
    embedded_source = WORK / 'embedded-source' / source.name
    embedded_source.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(source) as full, zipfile.ZipFile(embedded_source, 'w', zipfile.ZIP_STORED) as archive:
        for info in full.infolist():
            if info.filename.startswith(('deskpets/media/', 'img/')):
                continue
            archive.writestr(info.filename, full.read(info.filename))
        archive.writestr('ASSETS-DO-FONTE.txt',
            'Os assets deste código-fonte estão incluídos, sem alteração, na pasta\n'
            '_internal/deskpets/media da instalação. Após extrair este ZIP, copie\n'
            'essa pasta media para deskpets/media no fonte antes de compilar.\n'
            'O código Python, JSON, scripts de build, testes, licenças e créditos\n'
            'estão neste arquivo. As imagens img/ são screenshots da documentação\n'
            'original, disponível em https://github.com/Jumitti/DeskPets.\n')
    args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
            '--onedir', '--name', 'Muuri', '--distpath', str(WORK / 'dist'),
            '--workpath', str(WORK / 'build'), '--specpath', str(WORK),
            '--icon', str(ROOT / 'deskpets/media/muuri/muuri.ico'),
            '--additional-hooks-dir', str(ROOT / 'packaging/hooks'),
            '--exclude-module', 'PyQt6.QtWebEngineWidgets', '--exclude-module', 'PyQt6.QtWebEngineCore',
            '--exclude-module', 'PIL.AvifImagePlugin', '--exclude-module', 'PIL._avif']
    for src, dest in [(ROOT / 'deskpets/media', 'deskpets/media'),
                      (ROOT / 'deskpets/pets_data.json', 'deskpets'),
                      (defaults / 'pets_list.json', 'deskpets'), (defaults / 'config.json', 'deskpets'),
                      (ROOT / 'LICENSE', '.'), (ROOT / 'README.md', '.'),
                      (ROOT / 'packaging/LEIA-ME.txt', '.'), (licenses, 'THIRD_PARTY_LICENSES'),
                      (embedded_source, '.')]:
        args += ['--add-data', f'{src}:{dest}']
    args.append(str(ROOT / 'run.py'))
    # Ignore unrelated tools on the developer PATH when resolving native DLLs.
    env = os.environ.copy()
    windows = Path(os.environ['SystemRoot'])
    env['PATH'] = os.pathsep.join(map(str, [Path(sys.executable).parent,
        Path(sys.base_prefix), Path(sys.base_prefix) / 'DLLs',
        windows / 'System32', windows]))
    for key in ('PYTHONPATH', 'PYTHONHOME'):
        env.pop(key, None)
    subprocess.run(args, cwd=ROOT, env=env, check=True)
    analysis = (WORK / 'build/Muuri/Analysis-00.toc').read_text(encoding='utf-8')
    if 'codex-runtimes' in analysis or 'native\\poppler' in analysis:
        raise RuntimeError('Unrelated native libraries entered the bundle')
    shutil.copy2(source, OUTPUT / source.name)
    shutil.copy2(ROOT / 'packaging/LEIA-ME.txt', OUTPUT / 'COMO-INSTALAR-MUURI.txt')
    print('Executável pronto:', WORK / 'dist/Muuri/Muuri.exe')

if __name__ == '__main__':
    build()
