import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from deskpets import petworker


class MultiplePetLoaderTests(unittest.TestCase):
    def load(self, entries):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'pets_list.json'
            path.write_text(json.dumps({'pets': entries}), encoding='utf-8')
            def pet(species, color, fps, size, **kwargs):
                return SimpleNamespace(species=species, color=color, fps=fps, size=size,
                                       screen_width=1920, width=128, x=1792, **kwargs)
            with patch.object(petworker,'CONFIG_FILE',str(path)), patch.object(petworker,'Pet',side_effect=pet):
                return petworker.load_pets()

    def test_default_count_remains_one_and_disabled_pets_are_skipped(self):
        pets = self.load([dict(species='muuri',colors=['blue'],enabled=True),
                          dict(species='manu',colors=['blue'],enabled=False,count=30)])
        self.assertEqual(len(pets), 1)
        self.assertEqual((pets[0].species,pets[0].instance_index), ('muuri',0))

    def test_copies_per_color_have_distinct_identities_without_a_small_cap(self):
        pets = self.load([dict(species='dog',colors=['brown','white'],count=40),
                          dict(species='manu',colors=['blue'],count=35)])
        self.assertEqual(len(pets), 115)
        self.assertEqual(len({(p.species,p.color,p.instance_index) for p in pets}), 115)
        self.assertTrue(all(p.free_roam for p in pets))

    def test_invalid_counts_are_rejected(self):
        for count in (0, -1, True, 1.5, '2', None):
            with self.subTest(count=count), patch.object(petworker,'traceback'), patch('builtins.print'):
                with self.assertRaisesRegex(ValueError, 'Quantidade inválida'):
                    self.load([dict(species='manu',colors=['blue'],count=count)])
