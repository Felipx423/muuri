"""Tray actions exercise saved settings and window refresh without native pets."""
import collections
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PyQt6 import QtCore, QtWidgets

from deskpets import config_io, window
from deskpets.pets import PETS_DATA
from deskpets.petworker import MAX_PETS


class StubWorker(QtCore.QObject):
    frame_ready = QtCore.pyqtSignal(object, object)
    created = []

    def __init__(self, pets):
        super().__init__()
        self.pets = pets
        self.running = False
        self.waited = False
        self.created.append(self)

    def start(self):
        if any(worker.running for worker in self.created if worker is not self):
            raise AssertionError("The previous worker was not stopped")
        self.running = True

    def stop(self):
        self.running = False

    def wait(self, timeout=None):
        self.waited = True
        return not self.running


class StubDesktop:
    @staticmethod
    def close(pet):
        pet.closed = True

    @staticmethod
    def update_drag(pet):
        pass

    @staticmethod
    def update_physics(pet, elapsed):
        pass


class TrayPetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = Path(self.folder.name)
        self.list_path, self.config_path = root / "pets_list.json", root / "config.json"
        self.data = {
            "future_root": {"preserve": True},
            "pets": [
                {"species": species, "colors": colors, "enabled": species == "muuri",
                 "count": 2 if species == "muuri" else 1, "size": "Original",
                 "draggable": True, "physics_enabled": False,
                 "movement_multiplier": 1.25, "animation_multiplier": .75,
                 "future_field": [species, 42]}
                for species, colors in (("muuri", ["blue"]), ("fefo", ["green"]),
                                        ("eco", ["green"]), ("dog", ["brown", "white"]))
            ],
        }
        self.list_path.write_text(json.dumps(self.data), encoding="utf-8")
        self.config_path.write_text('{"layer":"front","future_setting":42}', encoding="utf-8")
        StubWorker.created = []
        self.patches = [
            patch.object(config_io, "LIST_FILE", self.list_path),
            patch.object(config_io, "CONFIG_FILE", self.config_path),
            patch.object(window, "load_pets", self.load_pets),
            patch.object(window, "PetWorker", StubWorker),
            patch.object(window, "Desktop", StubDesktop),
            patch.object(window, "IS_WINDOWS", False),
            patch.object(QtWidgets.QSystemTrayIcon, "show"),
            patch.object(QtWidgets.QMessageBox, "warning"),
        ]
        for item in self.patches:
            item.start()
        self.warning = QtWidgets.QMessageBox.warning
        self.owner = window.MainWindow(self.app)
        self.owner.drag_timer.stop()
        self.assertTrue(self.owner.start_refresh())
        self.tray = self.owner.tray_pets
        self.panel = self.owner.panel

    def tearDown(self):
        self.owner.shutdown()
        self.owner.hide()
        self.owner.deleteLater()
        self.app.processEvents()
        for item in reversed(self.patches):
            item.stop()
        self.folder.cleanup()

    def read(self):
        return config_io.read_json(self.list_path)

    def entry(self, species, document=None):
        return next(entry for entry in (document or self.read())["pets"] if entry["species"] == species)

    def load_pets(self):
        result = []
        for entry in self.read()["pets"]:
            if not entry.get("enabled", True):
                continue
            for color in entry.get("colors", []):
                for index in range(min(entry.get("count", 1), MAX_PETS - len(result))):
                    result.append(SimpleNamespace(
                        species=entry["species"], color=color, instance_index=index,
                        x=400, y=300, y_def=300, width=128, height=128,
                        screen_width=1920, screen_height=1080, free_roam=False,
                        state=SimpleNamespace(direction=1), physics_enabled=entry.get("physics_enabled", False),
                        motion=SimpleNamespace(vx=0, vy=0), closed=False,
                    ))
        return result

    def counts(self):
        return collections.Counter(pet.species for pet in self.owner.pets)

    def test_opening_menus_does_not_write_preferences_or_create_workers(self):
        before = self.list_path.read_bytes(), self.config_path.read_bytes()
        worker = self.owner.worker
        self.tray.rebuild()
        self.tray.rebuild()
        actions = self.owner.tray_icon.contextMenu().actions()
        self.assertIn("Remover todos os pets", [action.text() for action in actions])
        self.assertIn("Favoritos", [action.text() for action in actions])
        self.assertEqual((self.list_path.read_bytes(), self.config_path.read_bytes()), before)
        self.assertIs(self.owner.worker, worker)
        self.assertNotIn("favorite_species", self.read())
        self.assertFalse(self.panel.is_dirty())

    def test_remove_all_is_immediate_persistent_and_restores_configured_copies(self):
        old_pets, old_worker = list(self.owner.pets), self.owner.worker
        self.assertTrue(self.tray.remove_all_action.isEnabled())
        self.tray.remove_all_action.trigger()
        self.assertEqual(self.owner.pets, [])
        self.assertTrue(all(pet.closed for pet in old_pets))
        self.assertFalse(old_worker.running)
        self.assertTrue(old_worker.waited)
        self.assertFalse(self.tray.remove_all_action.isEnabled())
        self.assertTrue(all(not entry["enabled"] for entry in self.read()["pets"]))
        self.assertTrue(self.owner.start_refresh())
        self.assertEqual(self.owner.pets, [])
        self.assertTrue(self.tray.set_visible("muuri", True))
        self.assertEqual(self.counts(), {"muuri": 2})
        self.assertEqual(sum(worker.running for worker in StubWorker.created), 1)
        self.assertFalse(self.panel.is_dirty())

    def test_favorite_selection_and_removal_do_not_toggle_pets_or_restart_worker(self):
        worker, before_pets = self.owner.worker, list(self.owner.pets)
        self.assertTrue(self.tray.set_favorite("fefo", True))
        self.assertTrue(self.tray.set_favorite("muuri", True))
        self.assertTrue(self.tray.set_favorite("fefo", True))
        self.assertEqual(set(self.read()["favorite_species"]), {"fefo", "muuri"})
        self.assertEqual(len(self.read()["favorite_species"]), 2)
        self.assertEqual(self.owner.pets, before_pets)
        self.assertIs(self.owner.worker, worker)
        self.tray.rebuild()
        self.assertTrue(self.tray.visible_actions["muuri"].isChecked())
        self.assertFalse(self.tray.visible_actions["fefo"].isChecked())
        self.assertTrue(self.tray.set_favorite("muuri", False))
        self.assertEqual(self.read()["favorite_species"], ["fefo"])
        self.assertEqual(self.owner.pets, before_pets)
        self.assertIs(self.owner.worker, worker)
        self.assertFalse(self.panel.is_dirty())

    def test_menu_checkboxes_show_and_hide_all_copies_without_forgetting_favorite(self):
        self.assertTrue(self.tray.set_favorite("fefo", True))
        self.tray.rebuild()
        self.tray.visible_actions["fefo"].trigger()
        self.assertEqual(self.counts(), {"muuri": 2, "fefo": 1})
        self.assertTrue(self.tray.visible_actions["fefo"].isChecked())
        self.tray.visible_actions["fefo"].trigger()
        self.assertEqual(self.counts(), {"muuri": 2})
        self.assertFalse(self.tray.visible_actions["fefo"].isChecked())
        self.assertEqual(self.read()["favorite_species"], ["fefo"])
        self.assertTrue(self.owner.start_refresh())
        self.tray.rebuild()
        self.assertIn("fefo", self.tray.visible_actions)
        self.assertFalse(self.tray.visible_actions["fefo"].isChecked())

    def test_restored_pet_keeps_colors_count_unknown_fields_and_preferences(self):
        dog = copy.deepcopy(self.entry("dog"))
        self.assertTrue(self.tray.set_visible("dog", True))
        expected = copy.deepcopy(dog)
        expected["enabled"] = True
        self.assertEqual(self.entry("dog"), expected)
        self.assertEqual(self.counts(), {"muuri": 2, "dog": 2})
        self.assertEqual(sorted(pet.color for pet in self.owner.pets if pet.species == "dog"), ["brown", "white"])
        self.assertEqual(self.read()["future_root"], self.data["future_root"])
        self.assertEqual(config_io.read_json(self.config_path), {"layer": "front", "future_setting": 42})

    def test_pet_missing_saved_entry_and_zero_count_can_be_activated(self):
        data = self.read()
        self.entry("eco", data).update(colors=[], count=0)
        data["pets"] = [entry for entry in data["pets"] if entry["species"] != "fefo"]
        config_io.write_configs({self.list_path: data})
        self.assertTrue(self.tray.set_visible("eco", True))
        self.assertEqual(self.entry("eco")["colors"], ["green"])
        self.assertEqual(self.entry("eco")["count"], 1)
        self.assertTrue(self.tray.set_visible("fefo", True))
        self.assertEqual(self.entry("fefo")["colors"], [PETS_DATA["fefo"]["colors"][0]])
        self.assertTrue(self.entry("fefo")["draggable"])
        self.assertEqual(self.counts(), {"muuri": 2, "eco": 1, "fefo": 1})

    def test_six_pet_limit_rejects_whole_species_and_removal_frees_space(self):
        data = self.read()
        self.entry("muuri", data)["count"] = MAX_PETS
        config_io.write_configs({self.list_path: data})
        self.assertTrue(self.owner.start_refresh())
        before, worker = self.list_path.read_bytes(), self.owner.worker
        self.assertFalse(self.tray.set_visible("fefo", True))
        self.warning.assert_called_once()
        self.assertEqual(self.list_path.read_bytes(), before)
        self.assertIs(self.owner.worker, worker)
        self.assertEqual(self.counts(), {"muuri": MAX_PETS})
        self.assertTrue(self.tray.set_visible("muuri", False))
        self.assertTrue(self.tray.set_visible("fefo", True))
        self.assertEqual(self.counts(), {"fefo": 1})

    def test_save_failure_preserves_worker_settings_and_panel(self):
        before, draft, worker = self.list_path.read_bytes(), copy.deepcopy(self.panel.draft), self.owner.worker
        with patch.object(config_io, "write_configs", side_effect=PermissionError("read only")):
            self.assertFalse(self.tray.remove_all())
            self.assertFalse(self.tray.set_favorite("eco", True))
        self.assertEqual(self.warning.call_count, 2)
        self.assertEqual(self.list_path.read_bytes(), before)
        self.assertEqual(self.panel.draft, draft)
        self.assertIs(self.owner.worker, worker)
        self.assertTrue(worker.running)
        self.assertEqual(self.counts(), {"muuri": 2})

    def test_refresh_failure_rolls_back_saved_settings_and_reloads_old_pets(self):
        before = self.read()
        original, draft = copy.deepcopy(self.panel.original), copy.deepcopy(self.panel.draft)
        worker = self.owner.worker
        with patch.object(window, "load_pets", side_effect=[RuntimeError("temporary failure"), self.load_pets()]) as called, \
                patch.object(window, "traceback"), patch("builtins.print"):
            self.assertFalse(self.tray.remove_all())
            self.assertEqual(called.call_count, 2)
        self.assertEqual(self.read(), before)
        self.assertEqual(self.panel.original, original)
        self.assertEqual(self.panel.draft, draft)
        self.assertEqual(self.counts(), {"muuri": 2})
        self.assertFalse(worker.running)
        self.assertTrue(worker.waited)
        self.assertTrue(self.owner.worker.running)
        self.assertEqual(sum(worker.running for worker in StubWorker.created), 1)
        self.warning.assert_called_once()

    def test_choose_favorite_menu_only_changes_bookmarks(self):
        self.tray.rebuild()
        action = next(action for action in self.tray.choose_menu.actions() if action.text() == "Muuri")
        worker = self.owner.worker
        action.trigger()
        self.assertEqual(self.read()["favorite_species"], ["muuri"])
        self.assertEqual(self.counts(), {"muuri": 2})
        self.tray.rebuild()
        action = next(action for action in self.tray.choose_menu.actions() if action.text() == "Muuri")
        self.assertTrue(action.isChecked())
        action.trigger()
        self.assertEqual(self.read()["favorite_species"], [])
        self.assertEqual(self.counts(), {"muuri": 2})
        self.assertIs(self.owner.worker, worker)

    def test_remove_all_cancels_pending_pet_even_when_disk_already_has_none(self):
        self.assertTrue(self.tray.remove_all())
        self.panel.select("eco")
        self.panel.activate_selected()
        self.assertTrue(self.entry("eco", self.panel.draft)["enabled"])
        before, worker = self.list_path.read_bytes(), self.owner.worker
        self.assertTrue(self.tray.remove_all())
        self.assertFalse(self.entry("eco", self.panel.draft)["enabled"])
        self.assertEqual(self.list_path.read_bytes(), before)
        self.assertIs(self.owner.worker, worker)
        self.assertTrue(self.panel.apply())
        self.assertEqual(self.owner.pets, [])

    def test_remove_all_cancels_pending_activation_but_preserves_other_panel_edits(self):
        self.panel.select("muuri")
        self.panel.size.setCurrentIndex(self.panel.size.findData("Small"))
        self.panel.movement.setValue(175)
        self.panel.animation.setValue(150)
        self.panel.layer_combo.setCurrentIndex(self.panel.layer_combo.findData("back"))
        self.panel.select("eco")
        self.panel.activate_selected()
        self.assertTrue(self.panel.is_dirty())
        self.assertTrue(self.tray.remove_all())
        self.assertEqual(self.owner.pets, [])
        self.assertFalse(any(entry.get("enabled", True) for entry in self.panel.draft["pets"]))
        muuri = self.entry("muuri", self.panel.draft)
        self.assertEqual(muuri["size"], "Small")
        self.assertEqual(muuri["movement_multiplier"], 1.75)
        self.assertEqual(muuri["animation_multiplier"], 1.5)
        self.assertEqual(self.panel.layer, "back")
        self.assertTrue(self.panel.is_dirty())
        self.assertEqual(self.entry("muuri")["size"], "Original")
        self.assertTrue(self.panel.apply())
        self.assertEqual(self.owner.pets, [])
        self.assertEqual(self.entry("muuri")["size"], "Small")
        self.assertEqual(config_io.read_json(self.config_path)["layer"], "back")

    def test_favorite_editing_keeps_pending_panel_configuration_until_apply(self):
        self.panel.select("fefo")
        self.panel.activate_selected()
        self.panel.size.setCurrentIndex(self.panel.size.findData("Big"))
        worker = self.owner.worker
        self.assertTrue(self.tray.set_favorite("fefo", True))
        self.assertFalse(self.entry("fefo")["enabled"])
        self.assertEqual(self.entry("fefo")["size"], "Original")
        self.assertTrue(self.entry("fefo", self.panel.draft)["enabled"])
        self.assertEqual(self.entry("fefo", self.panel.draft)["size"], "Big")
        self.assertIs(self.owner.worker, worker)
        self.assertTrue(self.panel.apply())
        self.assertEqual(self.counts(), {"muuri": 2, "fefo": 1})
        self.assertEqual(self.read()["favorite_species"], ["fefo"])
        self.assertEqual(self.entry("fefo")["size"], "Big")

    def test_surviving_pet_position_and_orientation_are_preserved(self):
        self.owner.pets[0].x, self.owner.pets[0].y = 250, 160
        self.owner.pets[0].state.direction = -1
        self.assertTrue(self.tray.set_visible("eco", True))
        survivor = next(pet for pet in self.owner.pets if pet.species == "muuri" and pet.instance_index == 0)
        self.assertEqual((survivor.x, survivor.y, survivor.state.direction), (250, 160, -1))
        self.assertEqual(sum(worker.running for worker in StubWorker.created), 1)


if __name__ == "__main__":
    unittest.main()
