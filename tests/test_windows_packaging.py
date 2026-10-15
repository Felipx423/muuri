import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('muuri_windows_builder', ROOT/'packaging/build_windows.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class WindowsPackagingTests(unittest.TestCase):
    def test_sources_and_embedded_defaults_exclude_personal_preferences_and_build_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo, work = root/'repo', root/'work'
            (repo/'deskpets/media').mkdir(parents=True)
            work.mkdir()
            defaults = work/'defaults'
            defaults.mkdir()
            catalog = {name: {'colors': ['blue'], 'states': {'blue': {'idle': 'idle.gif', 'drag': 'drag.gif'}}}
                       for name in ('muuri', 'manu')}
            (repo/'deskpets/pets_data.json').write_text(json.dumps(catalog), encoding='utf-8')
            prefs = repo/'deskpets/pets_list.json'
            prefs.write_text('{"private_note":"DO_NOT_SHIP","pets":[]}', encoding='utf-8')
            (repo/'deskpets/config.json').write_text('{"private_layer":"DO_NOT_SHIP"}', encoding='utf-8')
            (repo/'deskpets/media/test.gif').write_bytes(b'original asset')
            (repo/'LICENSE').write_text('Original license', encoding='utf-8')
            for name in ('build/private.bin', 'dist/previous.zip', '.venv/private.txt', '.env', 'certificate.pfx'):
                path = repo/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'DO_NOT_SHIP')
            before = prefs.read_bytes()
            with patch.object(builder, 'ROOT', repo), patch.object(builder, 'WORK', work):
                source, embedded = builder.prepare_sources(defaults)
            self.assertEqual(prefs.read_bytes(), before)
            for path in (source, embedded):
                with zipfile.ZipFile(path) as archive:
                    self.assertIsNone(archive.testzip())
                    self.assertNotIn(b'DO_NOT_SHIP', b''.join(archive.read(name) for name in archive.namelist()))
                    data = json.loads(archive.read('deskpets/pets_list.json'))
                    self.assertEqual([entry['species'] for entry in data['pets'] if entry['enabled']], ['muuri'])
                    self.assertTrue(all(entry['count']==1 and entry['movement_multiplier']==entry['animation_multiplier']==1 for entry in data['pets']))
                    self.assertTrue(all(entry['draggable'] and entry['settings_clicks']==4 for entry in data['pets']))
                    self.assertEqual(json.loads(archive.read('deskpets/config.json')), {'layer': 'front'})
                    self.assertEqual(archive.read('LICENSE'), b'Original license')
                    self.assertEqual('deskpets/media/test.gif' in archive.namelist(), path==source)
