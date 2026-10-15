"""Run all tests using distribution defaults, without changing personal preferences."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build_macos import clean_defaults
from deskpets import config_io,petworker
from deskpets.desktop import IS_WINDOWS
if IS_WINDOWS:
    from deskpets import windows_API


def run():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        prefs,config = root/'pets_list.json',root/'config.json'
        prefs.write_text(json.dumps(clean_defaults()),encoding='utf-8')
        config.write_text('{"layer":"front"}',encoding='utf-8')
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(patch.object(config_io,'LIST_FILE',prefs))
            stack.enter_context(patch.object(config_io,'CONFIG_FILE',config))
            stack.enter_context(patch.object(petworker,'CONFIG_FILE',str(prefs)))
            stack.enter_context(patch.dict(os.environ,{'MUURI_CONFIG_DIR':str(root)}))
            if IS_WINDOWS:
                stack.enter_context(patch.object(windows_API,'CONFIG_FILE',str(config)))
            suite = unittest.defaultTestLoader.discover(str(ROOT/'tests'))
            result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':
    sys.exit(run())
