from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
import importlib.metadata

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent / 'work' / 'package'
OUTPUT = ROOT.parents[1] / 'outputs'


def write_version_marker():
    source = (ROOT / 'deskpets/version.py').read_text(encoding='utf-8')
    match = re.search(r'^\s*APP_VERSION\s*=\s*["\']([^"\']+)["\']\s*$', source, re.M)
    if not match:
        raise RuntimeError('Não foi possível determinar a versão do Muuri para o pacote')
    marker = WORK / 'MUURI-VERSION.txt'
    marker.write_text(match.group(1) + '\n', encoding='utf-8')
    return marker


def prepare_sources(defaults):
    catalog = json.loads((ROOT / 'deskpets/pets_data.json').read_text(encoding='utf-8'))
    data = {'pets': []}
    for species, info in catalog.items():
        color = info['colors'][0]
        interactive = 'drag' in info['states'][color]
        data['pets'].append(dict(species=species, colors=[color], enabled=species=='muuri',
                                size='Medium' if species=='muuri' else 'Original', count=1,
                                draggable=interactive, settings_clicks=4 if interactive else 0,
                                movement_multiplier=1.0, animation_multiplier=1.0, physics_enabled=False))
    (defaults / 'pets_list.json').write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding='utf-8')
    (defaults / 'config.json').write_text('{"layer": "front"}\n', encoding='utf-8')
    replacements = {f'deskpets/{name}': (defaults / name).read_bytes()
                    for name in ('pets_list.json', 'config.json')}
    source = WORK / 'Muuri-codigo-fonte.zip'
    excluded = {'.git', '.venv', '__pycache__', '.idea', '.vscode', 'build', 'dist',
                '.pytest_cache', '.mypy_cache', '.ruff_cache', 'htmlcov'}
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in ROOT.rglob('*'):
            rel = path.relative_to(ROOT)
            if any(part in excluded or part.endswith('.egg-info') for part in rel.parts):
                continue
            if path.is_file() and not (path.name.startswith('.env') or path.suffix in {'.pyc','.log','.p12','.pfx','.key'}):
                archive.writestr(rel.as_posix(), replacements.get(rel.as_posix(), path.read_bytes()))
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
    return source, embedded_source


def build():
    WORK.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    defaults = WORK / 'defaults'
    defaults.mkdir(exist_ok=True)
    source, embedded_source = prepare_sources(defaults)
    version_marker = write_version_marker()
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
    args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
            '--onedir', '--name', 'Muuri', '--distpath', str(WORK / 'dist'),
            '--workpath', str(WORK / 'build'), '--specpath', str(WORK),
            '--icon', str(ROOT / 'deskpets/media/muuri/muuri.ico'),
            '--additional-hooks-dir', str(ROOT / 'packaging/hooks'),
            '--exclude-module', 'PyQt6.QtWebEngineWidgets', '--exclude-module', 'PyQt6.QtWebEngineCore',
            '--exclude-module', 'PIL.AvifImagePlugin', '--exclude-module', 'PIL._avif',
            '--exclude-module', 'deskpets.macos_api', '--exclude-module', 'AppKit',
            '--exclude-module', 'Foundation', '--exclude-module', 'objc']
    for src, dest in [(ROOT / 'deskpets/media', 'deskpets/media'),
                      (ROOT / 'deskpets/pets_data.json', 'deskpets'),
                      (version_marker, 'deskpets'),
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
