import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
import win32con
import win32gui
from PyQt6 import QtCore, QtWidgets

from deskpets import config_io, petworker, windows_API
from deskpets.clicks import ClickSequence
from deskpets.pets import PETS_DATA, Pet
from deskpets.state import State
from deskpets.window import MainWindow, close, draw_pet_frame


class ClickTests(unittest.TestCase):
    def test_four_completed_clicks(self):
        sequence = ClickSequence()
        for index in range(4):
            sequence.press((100, 100), index * 0.25)
            self.assertEqual(sequence.release((104, 100), index * 0.25 + 0.05), index == 3)

    def test_slow_clicks_and_long_press_do_not_open(self):
        for spacing in (0.6, 2):
            sequence = ClickSequence()
            for index in range(4):
                sequence.press((0, 0), index * spacing)
                self.assertFalse(sequence.release((0, 0), index * spacing + 0.05))
        sequence.press((0, 0), 20)
        self.assertFalse(sequence.release((0, 0), 22))

    def test_drag_out_and_back_cancels(self):
        sequence = ClickSequence()
        for index in range(3):
            sequence.press((0, 0), index * 0.2)
            sequence.release((0, 0), index * 0.2 + 0.05)
        sequence.press((0, 0), 0.7)
        sequence.move((7, 0))
        self.assertFalse(sequence.release((0, 0), 0.8))
        self.assertEqual(sequence.count, 0)

    def test_exact_distance_and_deadline(self):
        sequence = ClickSequence()
        for index in range(4):
            sequence.press((0, 0), index * 0.45)
            self.assertEqual(sequence.release((6, 0), index * 0.45 + 0.1), index == 3)


class SaveTests(unittest.TestCase):
    def test_second_replace_failure_restores_both_files(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder)/"pets.json", Path(folder)/"config.json"
            first.write_bytes(b'{"old": 1}')
            second.write_bytes(b'{"old": 2}')
            original_replace = config_io.os.replace

            def replace(source, destination):
                if destination == second:
                    raise PermissionError("test failure")
                original_replace(source, destination)

            with patch.object(config_io.os, "replace", side_effect=replace):
                with self.assertRaises(PermissionError):
                    config_io.write_configs({first: {"new": 1}, second: {"new": 2}})
            self.assertEqual(first.read_bytes(), b'{"old": 1}')
            self.assertEqual(second.read_bytes(), b'{"old": 2}')
            self.assertEqual(len(list(Path(folder).iterdir())), 2)


class PanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        folder = Path(self.folder.name)
        self.list_path, self.config_path = folder/"pets_list.json", folder/"config.json"
        self.data = config_io.read_json(config_io.LIST_FILE)
        self.data["future_root"] = {"keep": True}
        self.muuri = next(e for e in self.data["pets"] if e["species"] == "muuri")
        self.muuri.update(size="Original", movement_multiplier=1, animation_multiplier=1,
                          enabled=True, draggable=True, physics_enabled=False)
        self.muuri["future_field"] = "preserve"
        self.list_path.write_text(json.dumps(self.data), encoding="utf-8")
        self.config_path.write_text('{"layer":"front","future_setting":42}', encoding="utf-8")
        self.patches = [patch.object(config_io, "LIST_FILE", self.list_path),
                        patch.object(config_io, "CONFIG_FILE", self.config_path),
                        patch.object(petworker, "CONFIG_FILE", str(self.list_path)),
                        patch.object(windows_API, "CONFIG_FILE", str(self.config_path))]
        for item in self.patches:
            item.start()
        self.window = MainWindow(self.app)
        self.assertTrue(self.window.start_refresh())
        self.window.worker.stop()
        self.window.worker.wait(3000)
        self.window.drag_timer.stop()
        self.panel = self.window.panel

    def tearDown(self):
        self.window.shutdown()
        self.window.hide()
        self.window.deleteLater()
        self.app.processEvents()
        for item in reversed(self.patches):
            item.stop()
        self.folder.cleanup()

    def pet(self):
        return next(p for p in self.window.pets if p.species == "muuri")

    def test_open_preview_and_discard_never_save(self):
        before = self.list_path.read_bytes(), self.config_path.read_bytes()
        self.assertEqual(self.panel.species, "muuri")
        self.assertFalse(self.panel.is_dirty())
        self.assertFalse(self.window.isVisible())
        self.window.show_settings_for_pet("muuri")
        self.assertTrue(self.window.isVisible())
        old_width, old_height = self.pet().width, self.pet().height
        self.panel.size.setCurrentIndex(self.panel.size.findData("Big"))
        self.panel.movement.setValue(150)
        self.panel.animation.setValue(200)
        self.assertTrue(self.panel.is_dirty())
        self.assertEqual((self.pet().width, self.pet().height), (old_width, old_height))
        self.assertEqual((self.list_path.read_bytes(), self.config_path.read_bytes()), before)
        self.panel.discard()
        self.assertFalse(self.panel.is_dirty())
        self.assertEqual(self.panel.size.currentData(), "Original")
        self.assertEqual((self.list_path.read_bytes(), self.config_path.read_bytes()), before)

    def test_apply_preserves_unknowns_position_direction_and_persists(self):
        pet = self.pet()
        pet.x, pet.y, pet.y_def = 200, 150, 150
        pet.free_roam = True
        pet.state.direction = -1
        old_worker = self.window.worker
        old_hwnd = pet.hwnd
        self.panel.size.setCurrentIndex(self.panel.size.findData("Small"))
        self.panel.movement.setValue(150)
        self.panel.animation.setValue(200)
        self.panel.draggable.setChecked(False)
        self.panel.layer_combo.setCurrentIndex(1)
        initial = []
        original_start = petworker.PetWorker.start

        def start(worker):
            p = next(p for p in worker.pets if p.species == "muuri")
            initial.append((p.x, p.y, p.state.direction))
            original_start(worker)

        with patch.object(petworker.PetWorker, "start", start):
            self.assertTrue(self.panel.apply())
        self.window.worker.stop()
        self.window.worker.wait(3000)
        saved = config_io.read_json(self.list_path)
        entry = next(e for e in saved["pets"] if e["species"] == "muuri")
        self.assertEqual(entry["future_field"], "preserve")
        self.assertEqual(entry["settings_clicks"], 4)
        self.assertEqual(entry["movement_multiplier"], 1.5)
        self.assertEqual(entry["animation_multiplier"], 2)
        self.assertEqual(saved["future_root"], {"keep": True})
        self.assertEqual(config_io.read_json(self.config_path), {"layer": "back", "future_setting": 42})
        self.assertFalse(old_worker.isRunning())
        self.assertFalse(win32gui.IsWindow(old_hwnd))
        pet = self.pet()
        self.assertEqual(initial, [(200, 150, -1)])
        self.assertEqual((pet.y, pet.y_def, pet.state.direction, pet.height), (150, 150, -1, 40))
        self.assertFalse(pet.draggable)
        self.assertFalse(win32gui.GetWindowLong(pet.hwnd, win32con.GWL_EXSTYLE) & windows_API.WS_EX_TRANSPARENT)
        self.assertFalse(self.panel.is_dirty())
        self.assertTrue(self.window.start_refresh())
        self.window.worker.stop()
        self.window.worker.wait(3000)
        self.assertEqual(self.pet().animation_multiplier, 2)

    def test_only_preferences_does_not_rewrite_pet_list(self):
        before = self.list_path.read_bytes()
        self.panel.layer_combo.setCurrentIndex(1)
        self.assertEqual(self.panel.draft, self.panel.original)
        self.assertTrue(self.panel.apply())
        self.assertEqual(self.list_path.read_bytes(), before)

    def test_physics_toggle_only_applies_on_confirmation(self):
        before = self.list_path.read_bytes()
        self.assertFalse(self.pet().physics_enabled)
        self.panel.physics.setChecked(True)
        self.assertTrue(self.panel.is_dirty())
        self.assertFalse(self.pet().physics_enabled)
        self.assertEqual(self.list_path.read_bytes(), before)
        self.panel.discard()
        self.assertFalse(self.panel.physics.isChecked())
        self.panel.physics.setChecked(True)
        self.assertTrue(self.panel.apply())
        self.assertTrue(self.pet().physics_enabled)
        self.window.worker.stop()
        self.window.worker.wait(3000)
        self.pet().x, self.pet().y = 200, 100
        self.pet().motion.vx = 100
        self.pet().motion.vy = 200
        windows_API.Windows.update_physics(self.pet(), 0.016)
        self.assertGreater(self.pet().y, 100)
        self.assertGreater(self.pet().x, 200)
        self.assertEqual(win32gui.GetWindowRect(self.pet().hwnd)[:2], (int(self.pet().x), int(self.pet().y)))
        self.pet().update_state()
        self.assertEqual(self.pet().state.name, "drag")
        position = self.pet().x, self.pet().y
        self.panel.physics.setChecked(False)
        self.assertTrue(self.panel.apply())
        self.window.worker.stop()
        self.window.worker.wait(3000)
        self.assertFalse(self.pet().physics_enabled)
        self.assertEqual(self.pet().y, position[1])
        self.assertEqual(self.pet().motion.vy, 0)

    def test_native_drag_launches_and_press_stops_motion(self):
        pet = self.pet()
        pet.physics_enabled = True
        pet.x, pet.y = 200, 100
        point = 20 | (20 << 16)
        with patch("deskpets.physics.time.monotonic", return_value=100):
            win32gui.SendMessage(pet.hwnd, win32con.WM_LBUTTONDOWN, 1, point)
        with patch("deskpets.physics.time.monotonic", return_value=100.05):
            windows_API.Windows.move_drag(pet, 250, 100)
        with patch("deskpets.physics.time.monotonic", return_value=100.06):
            win32gui.SendMessage(pet.hwnd, win32con.WM_LBUTTONUP, 0, point)
        self.assertGreater(pet.motion.vx, 0)
        self.assertLess(pet.motion.vy, 0)
        win32gui.SendMessage(pet.hwnd, win32con.WM_LBUTTONDOWN, 1, point)
        self.assertEqual((pet.motion.vx, pet.motion.vy), (0, 0))
        before = pet.x, pet.y
        windows_API.Windows.update_physics(pet, 0.016)
        self.assertEqual((pet.x, pet.y), before)
        windows_API.Windows.end_drag(pet)

    def test_physics_timer_moves_pet_while_panel_is_hidden(self):
        pet = self.pet()
        pet.physics_enabled = True
        pet.x, pet.y = 200, 100
        pet.motion.vx = 400
        self.window.last_physics_update = time.monotonic()
        self.window.drag_timer.start(16)
        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(160, loop.quit)
        loop.exec()
        self.window.drag_timer.stop()
        self.assertFalse(self.window.isVisible())
        self.assertGreater(pet.x, 200)
        self.assertGreater(pet.y, 100)
        self.assertEqual(win32gui.GetWindowRect(pet.hwnd)[:2], (int(pet.x), int(pet.y)))

    def test_select_and_apply_replaces_pet_and_supplies_default_color(self):
        before = self.list_path.read_bytes()
        old_pet = self.pet()
        for index in range(self.panel.species_list.count()):
            if self.panel.species_list.item(index).data(QtCore.Qt.ItemDataRole.UserRole) == "clippy":
                self.panel.species_list.setCurrentRow(index)
                break
        self.assertTrue(self.panel.is_dirty())
        self.assertTrue(self.panel.enabled.isChecked())
        self.assertTrue(any(check.isChecked() for check in self.panel.color_checks.values()))
        self.assertEqual(self.list_path.read_bytes(), before)
        self.assertIs(self.pet(), old_pet)
        self.assertTrue(self.panel.apply())
        self.window.worker.stop()
        self.window.worker.wait(3000)
        self.assertEqual({p.species for p in self.window.pets}, {"clippy"})
        saved = config_io.read_json(self.list_path)
        self.assertEqual([e["species"] for e in saved["pets"] if e.get("enabled")], ["clippy"])
        muuri = next(e for e in saved["pets"] if e["species"] == "muuri")
        self.assertEqual(muuri["size"], "Original")
        self.assertEqual(muuri["settings_clicks"], 4)

    def test_discard_selection_and_click_same_row_again(self):
        before = self.list_path.read_bytes()
        self.panel.select("dog")
        self.assertFalse(self.panel.is_dirty())
        self.panel.activate_selected(self.panel.species_list.currentItem())
        self.assertTrue(self.panel.is_dirty())
        self.panel.discard()
        self.assertFalse(self.panel.is_dirty())
        self.assertEqual(self.list_path.read_bytes(), before)
        self.panel.activate_selected(self.panel.species_list.currentItem())
        self.assertTrue(self.panel.apply())
        self.window.worker.stop()
        self.window.worker.wait(3000)
        self.assertEqual({p.species for p in self.window.pets}, {"dog"})

    def test_save_failure_retains_draft_and_live_pet(self):
        before = self.list_path.read_bytes()
        pet = self.pet()
        self.panel.animation.setValue(150)
        with patch.object(config_io, "write_configs", side_effect=PermissionError("Acesso negado")), \
                patch.object(QtWidgets.QMessageBox, "warning") as warning:
            self.assertFalse(self.panel.apply())
            warning.assert_called_once()
        self.assertEqual(self.list_path.read_bytes(), before)
        self.assertIs(self.pet(), pet)
        self.assertTrue(self.panel.is_dirty())
        self.assertIn("Não foi possível", self.panel.status.text())

    def test_enabled_pet_requires_color(self):
        self.panel.color_checks["blue"].setChecked(False)
        with patch.object(QtWidgets.QMessageBox, "warning"):
            self.assertFalse(self.panel.apply())
        self.assertTrue(self.panel.is_dirty())

    def test_all_species_previews_and_muuri_seven_states_sizes_mirroring(self):
        before = self.list_path.read_bytes()
        for index in range(self.panel.species_list.count()):
            self.panel.species_list.setCurrentRow(index)
            self.assertTrue(self.panel.preview.frames, self.panel.species)
        self.panel.select("muuri")
        self.assertEqual(self.panel.preview_state.count(), 7)
        for index in range(7):
            self.panel.preview_state.setCurrentIndex(index)
            frame = self.panel.preview.frames[0]
            self.assertEqual(frame.pixelColor(0, 0).alpha(), 0)
            self.panel.preview_direction.setCurrentIndex(1)
            self.assertEqual(self.panel.preview.direction, -1)
            self.panel.preview_direction.setCurrentIndex(0)
        for key, height in (("Very Small", 20), ("Small", 40), ("Original", 64),
                            ("Medium", 125), ("Big", 150), ("Really Big", 200)):
            self.panel.size.setCurrentIndex(self.panel.size.findData(key))
            self.assertEqual(self.panel.preview.frames[0].height(), height)
        self.assertEqual(self.list_path.read_bytes(), before)

    def test_movement_and_animation_are_independent(self):
        pet = self.pet()
        info = pet.STATES_INFO["walk"]
        pet.state = State("walk", info["gif"], hold=32, movement_speed=2, speed_animation=1)
        pet.movement_multiplier, pet.animation_multiplier = 1.5, 2
        pet.frame_animation()
        self.assertEqual(pet.state_interval, 1/8)
        self.assertEqual(pet.frame_interval, 1/16)
        pet.x = 100
        self.assertFalse(pet.state.next(pet))
        self.assertEqual(pet.x, 103)
        for _ in range(30):
            self.assertFalse(pet.state.next(pet))
        self.assertTrue(pet.state.next(pet))
        self.assertEqual(pet.state.counter * pet.state_interval, 4)
        pet.animation_multiplier = 0.5
        pet.frame_animation()
        self.assertEqual(pet.state_interval, 1/8)
        self.assertEqual(pet.frame_interval, 1/4)
        for name in ("idle", "lie", "swipe", "drag"):
            info = pet.STATES_INFO[name]
            state = State(name, info["gif"], movement_speed=info["movement_speed"])
            before = pet.x, pet.y
            state.next(pet)
            self.assertEqual((pet.x, pet.y), before)

    def test_native_double_clicks_count_once_and_drag_disabled_still_opens(self):
        pet = self.pet()
        pet.draggable = False
        hwnd = pet.hwnd
        point = 20 | (20 << 16)
        for index in range(4):
            message = win32con.WM_LBUTTONDOWN if index % 2 == 0 else win32con.WM_LBUTTONDBLCLK
            win32gui.SendMessage(hwnd, message, 1, point)
            # A duplicate notification while pressed is not another click.
            win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDBLCLK, 1, point)
            win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, point)
            self.app.processEvents()
            self.assertEqual(self.window.isVisible(), index == 3)
        self.assertEqual(self.panel.species, "muuri")
        self.assertIs(self.pet(), pet)
        self.assertIs(self.window.centralWidget(), self.panel)

    def test_native_drag_cancels_click_sequence_and_restores_state(self):
        pet = self.pet()
        point = 20 | (20 << 16)
        for _ in range(3):
            win32gui.SendMessage(pet.hwnd, win32con.WM_LBUTTONDOWN, 1, point)
            win32gui.SendMessage(pet.hwnd, win32con.WM_LBUTTONUP, 0, point)
        previous = pet.state
        win32gui.SendMessage(pet.hwnd, win32con.WM_LBUTTONDOWN, 1, point)
        windows_API.Windows.move_drag(pet, 220, 170)
        pet.update_state()
        self.assertEqual(pet.state.name, "drag")
        self.assertEqual((pet.x, pet.y), (200, 150))
        win32gui.SendMessage(pet.hwnd, win32con.WM_LBUTTONUP, 0, point)
        self.app.processEvents()
        self.assertFalse(self.window.isVisible())
        pet.update_state()
        self.assertIs(pet.state, previous)
        self.assertEqual(pet.click_sequence.count, 0)

    def test_sequence_pauses_movement_until_it_expires(self):
        pet = self.pet()
        pet.state = State("walk", pet.STATES_INFO["walk"]["gif"], hold=1000, movement_speed=2)
        pet.x, pet.y, pet.free_roam, pet.immunity = 100, 100, True, True
        now = time.monotonic()
        pet.click_sequence.press((100, 100), now)
        pet.click_sequence.release((100, 100), now+0.01)
        pet.update_state()
        self.assertEqual((pet.x, pet.state.counter), (100, 0))
        with patch("deskpets.pets.time.monotonic", return_value=now+1.6):
            pet.update_state()
        self.assertEqual((pet.x, pet.state.counter), (102, 1))

    def test_worker_cadence_keeps_duration_and_displacement(self):
        results = []
        for animation in (0.5, 1, 2):
            state = State("walk", "unused", hold=32, movement_speed=2)
            clock, transitions, frames = [100.0], [], []
            pet = SimpleNamespace(state=state, state_interval=1/8, frame_interval=1/(8*animation),
                                  frames=[Image.new("RGBA", (1, 1), "blue")], current_frame=0, frame_count=1,
                                  x=1000, y=100, screen_width=10000, width=1, movement_multiplier=1.5)

            def update():
                if state.next(pet) and not transitions:
                    transitions.append(clock[0])

            pet.update_state = update
            worker = petworker.PetWorker([pet])
            worker.frame_ready.connect(lambda p, frame: frames.append(frame), QtCore.Qt.ConnectionType.DirectConnection)

            def sleep(interval):
                clock[0] += interval
                if clock[0] >= 104.2:
                    worker.stop()

            with patch.object(petworker.time, "time", side_effect=lambda: clock[0]), \
                    patch.object(petworker.time, "sleep", side_effect=sleep):
                worker.run()
            results.append((state.counter, pet.x, transitions[0], len(frames)))
        self.assertEqual([r[:3] for r in results], [results[0][:3]]*3)
        self.assertLess(results[0][3], results[1][3])
        self.assertLess(results[1][3], results[2][3])

    def test_restart_reads_saved_choices(self):
        self.panel.animation.setValue(175)
        self.assertTrue(self.panel.apply())
        other = MainWindow(self.app)
        try:
            self.assertEqual(other.panel.animation.value(), 175)
            self.assertFalse(other.panel.is_dirty())
            self.assertTrue(other.start_refresh())
            other.worker.stop()
            other.worker.wait(3000)
            self.assertEqual(other.pets[0].animation_multiplier, 1.75)
        finally:
            other.shutdown()
            other.deleteLater()

    def test_other_species_render_and_retain_original_click_through(self):
        for species in ("chicken", "dog", "squirrel"):
            color = PETS_DATA[species]["colors"][0]
            pet = Pet(species, color, 8, "Small")
            try:
                self.assertEqual((pet.animation_multiplier, pet.movement_multiplier), (1, 1))
                self.assertTrue(win32gui.GetWindowLong(pet.hwnd, win32con.GWL_EXSTYLE) & windows_API.WS_EX_TRANSPARENT)
                draw_pet_frame(pet, pet.frames[0])
            finally:
                close(pet)

    def test_refresh_failure_rolls_back_saved_documents(self):
        before = config_io.read_json(self.list_path)
        self.panel.animation.setValue(150)
        with patch.object(self.window, "start_refresh", side_effect=[False, True]), \
                patch.object(QtWidgets.QMessageBox, "warning"):
            self.assertFalse(self.panel.apply())
        self.assertEqual(config_io.read_json(self.list_path), before)
        self.assertTrue(self.panel.is_dirty())

    def test_close_dialog_all_three_choices(self):
        self.panel.movement.setValue(125)
        for text, expected in (("Continuar editando", False), ("Descartar", True), ("Aplicar", True)):
            self.panel.movement.setValue(125)

            # Replace exec only; the real custom buttons and decision logic remain.
            active = False

            def execute(box):
                nonlocal active
                if not active:
                    active = True
                    box._test_clicked = next(b for b in box.buttons() if b.text() == text)
                return 0

            with patch.object(QtWidgets.QMessageBox, "exec", execute), \
                    patch.object(QtWidgets.QMessageBox, "clickedButton", lambda box: box._test_clicked):
                self.assertEqual(self.panel.allow_close(), expected)


if __name__ == "__main__":
    unittest.main()
