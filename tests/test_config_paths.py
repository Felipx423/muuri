import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from deskpets import config_io


class ConfigPathTests(unittest.TestCase):
    def test_macos_uses_user_application_support_and_windows_keeps_existing_path(self):
        with patch.dict(os.environ,{'MUURI_CONFIG_DIR':''}), \
                patch.object(config_io,'sys',SimpleNamespace(platform='darwin')), \
                patch('PyQt6.QtCore.QStandardPaths.writableLocation',return_value='/Users/example/Library/Application Support'):
            self.assertEqual(config_io.configuration_dir(),Path('/Users/example/Library/Application Support/Muuri'))
        with patch.dict(os.environ,{'MUURI_CONFIG_DIR':''}),patch.object(config_io,'sys',SimpleNamespace(platform='win32')):
            self.assertEqual(config_io.configuration_dir(),config_io.BASE_DIR)

    def test_explicit_test_override_uses_only_requested_directory(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'MUURI_CONFIG_DIR':folder}):
            self.assertEqual(config_io.configuration_dir(),Path(folder).resolve())

    def test_initialize_defaults_once_and_keep_existing_preferences_unknown_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/'Muuri'
            prefs,config = root/'pets_list.json',root/'config.json'
            with patch.object(config_io,'LIST_FILE',prefs),patch.object(config_io,'CONFIG_FILE',config):
                config_io.initialize_configs()
                self.assertTrue(prefs.exists() and config.exists())
                data = json.loads(prefs.read_text(encoding='utf-8'))
                data['future_setting'] = {'keep':True}
                data['pets'][0]['animation_multiplier'] = 1.37
                prefs.write_text(json.dumps(data),encoding='utf-8')
                before = prefs.read_bytes(),config.read_bytes()
                config_io.initialize_configs()
                self.assertEqual((prefs.read_bytes(),config.read_bytes()),before)
