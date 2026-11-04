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
            before = path.read_bytes()
            created = []
            def pet(species, color, fps, size, **kwargs):
                result = SimpleNamespace(species=species, color=color, fps=fps, size=size,
                                       screen_width=1920, width=128, x=1792, **kwargs)
                created.append(result)
                return result
            with patch.object(petworker,'CONFIG_FILE',str(path)), patch.object(petworker,'Pet',side_effect=pet):
                pets = petworker.load_pets()
            self.assertLessEqual(len(created), 6)
            self.assertEqual(path.read_bytes(), before)
            return pets

    def test_default_count_remains_one_and_disabled_pets_are_skipped(self):
        pets = self.load([dict(species='muuri',colors=['blue'],enabled=True),
                          dict(species='manu',colors=['blue'],enabled=False,count=30)])
        self.assertEqual(len(pets), 1)
        self.assertEqual((pets[0].species,pets[0].instance_index), ('muuri',0))

    def test_six_pet_limit_counts_all_colors_and_keeps_distinct_identities(self):
        pets = self.load([dict(species='dog',colors=['brown','white'],count=4),
                          dict(species='manu',colors=['blue'],count=35)])
        self.assertEqual(len(pets), 6)
        self.assertEqual([p.color for p in pets], ['brown']*4+['white']*2)
        self.assertEqual(len({(p.species,p.color,p.instance_index) for p in pets}), 6)
        self.assertTrue(all(p.free_roam for p in pets))

    def test_limit_is_global_across_species_and_bounds_huge_legacy_counts(self):
        pets = self.load([dict(species='muuri',colors=['blue'],count=5),
                          dict(species='eco',colors=['green'],count=2)])
        self.assertEqual([p.species for p in pets], ['muuri']*5+['eco'])
        pets = self.load([dict(species='muuri',colors=['blue'],count=10**100)])
        self.assertEqual(len(pets), 6)

    def test_invalid_counts_are_rejected(self):
        for count in (0, -1, True, 1.5, '2', None):
            with self.subTest(count=count), patch.object(petworker,'traceback'), patch('builtins.print'):
                with self.assertRaisesRegex(ValueError, 'Quantidade inválida'):
                    self.load([dict(species='manu',colors=['blue'],count=count)])
