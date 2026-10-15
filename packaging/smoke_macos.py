"""Start the frozen app in isolation; visual desktop QA remains a separate step."""
import json
import os
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


if __name__=='__main__':
    smoke(Path(sys.argv[1]).resolve())
