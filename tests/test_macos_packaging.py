import argparse
import importlib.util
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('muuri_macos_builder',ROOT/'packaging/build_macos.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class MacOSPackagingTests(unittest.TestCase):
    def test_sources_are_complete_with_clean_preferences_and_executable_command(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo,work,output = root/'repo',root/'work',root/'out'
            (repo/'deskpets/media/muuri').mkdir(parents=True)
            (repo/'packaging').mkdir()
            catalog = {'muuri':{'colors':['blue'],'states':{'blue':{'idle':'media/muuri/idle.gif','drag':'drag.gif'}}},
                       'manu':{'colors':['blue'],'states':{'blue':{'idle':'idle.gif','drag':'drag.gif'}}}}
            (repo/'deskpets/pets_data.json').write_text(json.dumps(catalog),encoding='utf-8')
            (repo/'deskpets/pets_list.json').write_text('{"private_note":"DO_NOT_SHIP"}',encoding='utf-8')
            (repo/'deskpets/config.json').write_text('{"private_setting":"DO_NOT_SHIP"}',encoding='utf-8')
            (repo/'packaging/MACOS.md').write_text('Build instructions',encoding='utf-8')
            (repo/'packaging/BUILD-MACOS.command').write_text('#!/bin/bash\n',encoding='utf-8')
            (repo/'LICENSE').write_text('Original license',encoding='utf-8')
            icon = ROOT/'deskpets/media/muuri/muuri.ico'
            shutil.copy2(icon,repo/'deskpets/media/muuri/muuri.ico')
            with patch.object(builder,'ROOT',repo),patch.object(builder,'WORK',work),patch.object(builder,'OUTPUT',output):
                defaults,source,embedded,icns = builder.prepare()
                self.assertTrue(icns.exists())
                with zipfile.ZipFile(source) as archive:
                    self.assertEqual(archive.read('LICENSE'),b'Original license')
                    prefs = json.loads(archive.read('deskpets/pets_list.json'))
                    self.assertEqual([e['species'] for e in prefs['pets'] if e['enabled']],['muuri'])
                    self.assertTrue(all(e['count']==1 and e['animation_multiplier']==1 for e in prefs['pets']))
                    self.assertNotIn('DO_NOT_SHIP',archive.read('deskpets/pets_list.json').decode())
                    self.assertEqual(json.loads(archive.read('deskpets/config.json')),{'layer':'front'})
                    self.assertEqual(archive.read('deskpets/media/muuri/muuri.ico'),icon.read_bytes())
                    self.assertTrue(archive.getinfo('packaging/BUILD-MACOS.command').external_attr >> 16 & 0o111)
                with zipfile.ZipFile(embedded) as archive:
                    self.assertNotIn('deskpets/media/muuri/muuri.ico',archive.namelist())
                    self.assertIn('ASSETS-DO-FONTE.txt',archive.namelist())

    def test_real_app_build_is_rejected_on_windows_before_creating_outputs(self):
        with patch.object(builder,'sys',SimpleNamespace(platform='win32')),patch.object(builder,'prepare') as prepare:
            with self.assertRaisesRegex(RuntimeError,'Mac com Python arm64'):
                builder.build(argparse.Namespace(prepare_only=False,dmg=False,codesign_identity=None))
            prepare.assert_not_called()
