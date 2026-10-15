"""Start the frozen app in isolation; visual desktop QA remains a separate step."""
import argparse
import os
import plistlib
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def smoke(app):
    if sys.platform!='darwin':
        raise RuntimeError('Este teste de .app precisa de macOS')
    executable = app/'Contents/MacOS/Muuri'
    resources = app/'Contents/Resources/deskpets'
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        for name in ('pets_list.json','config.json'):
            (root/name).write_bytes((resources/name).read_bytes())
        env = os.environ.copy()
        env['MUURI_CONFIG_DIR']=str(root)
        env['PATH']='/usr/bin:/bin:/usr/sbin:/sbin'
        for name in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV'):
            env.pop(name,None)
        with (root/'startup.log').open('w') as log:
            proc = subprocess.Popen([str(executable)],env=env,stdout=log,stderr=log)
            try:
                time.sleep(5)
                if proc.poll() is not None:
                    raise RuntimeError('O aplicativo encerrou no início: '+(root/'startup.log').read_text())
                for _ in range(2):
                    second = subprocess.run([str(executable)],env=env,capture_output=True,timeout=15)
                    if second.returncode!=0:
                        raise RuntimeError('Segunda execução não encerrou corretamente')
            finally:
                proc.terminate()
                proc.wait(timeout=15)
        print('PASS .app inicia sem Python no PATH e bloqueia execuções duplicadas; preferências isoladas.')


def smoke_dmg(image):
    if sys.platform!='darwin':
        raise RuntimeError('Este teste de DMG precisa de macOS')
    with tempfile.TemporaryDirectory(prefix='muuri-install-') as folder:
        root = Path(folder)
        mount = root/'volume'
        result = subprocess.run(['hdiutil','attach','-readonly','-nobrowse','-plist',
                                 '-mountpoint',str(mount),str(image)],
                                check=True,capture_output=True)
        try:
            entities = plistlib.loads(result.stdout)['system-entities']
            if not any(item.get('mount-point')==str(mount) for item in entities):
                raise RuntimeError('O DMG não foi montado no diretório de teste')
            target = root/'Applications/Muuri.app'
            target.parent.mkdir()
            subprocess.run(['ditto',str(mount/'Muuri.app'),str(target)],check=True)
        finally:
            subprocess.run(['hdiutil','detach',str(mount)],check=True)
        subprocess.run(['codesign','--verify','--deep','--strict',str(target)],check=True)
        smoke(target)
        print('PASS DMG monta, instala uma cópia independente e inicia após desmontar a imagem.')


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path',type=Path)
    parser.add_argument('--dmg',action='store_true')
    args = parser.parse_args()
    (smoke_dmg if args.dmg else smoke)(args.path.resolve())
