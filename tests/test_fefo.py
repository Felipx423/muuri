import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from PyQt6 import QtCore, QtWidgets
import win32con
import win32gui

from deskpets import config_io, petworker, windows_API
from deskpets.pets import PETS_DATA
from deskpets.state import State
from deskpets.window import MainWindow, draw_pet_frame


STATES = {'idle', 'walk', 'walk_fast', 'run', 'swipe', 'lie', 'drag', 'fly'}


class FefoAssetTests(unittest.TestCase):
    def test_eight_states_original_128_alpha_loop_and_palette(self):
        data = PETS_DATA['fefo']
        self.assertEqual(data['colors'], ['green'])
        self.assertEqual(set(data['states']['green']), STATES)
        for state, path in data['states']['green'].items():
            with self.subTest(state=state), Image.open(config_io.BASE_DIR / path) as gif:
                self.assertEqual(gif.size, (128, 128))
                self.assertEqual(gif.n_frames, 8)
                self.assertEqual(gif.info['loop'], 0)
                decoded = []
                for index in range(8):
                    gif.seek(index)
                    self.assertEqual(gif.info['duration'], 120 if index % 2 == 0 else 130)
                    self.assertEqual(gif.disposal_method, 2)
                    frame = gif.convert('RGBA')
                    left, top, right, bottom = frame.getchannel('A').getbbox()
                    self.assertTrue(0 < left < right < 128 and 0 < top < bottom < 128)
                    self.assertEqual(frame.getpixel((0, 0))[3], 0)
                    raw = frame.tobytes()
                    colors = list(zip(raw[0::4],raw[1::4],raw[2::4],raw[3::4]))
                    green = sum(a == 255 and g > r * 1.15 and g > b * 1.2 for r,g,b,a in colors)
                    purple = sum(a == 255 and b > g * 1.2 and r > g * 1.2 for r,g,b,a in colors)
                    self.assertGreater(green, 1000, 'Green body became transparent or discolored')
                    self.assertGreater(purple, 40, 'Purple feathers disappeared')
                    decoded.append(frame.tobytes())
                self.assertGreater(len(set(decoded)), 3, 'State has no meaningful frame changes')


class FefoIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        folder = Path(self.folder.name)
        self.list_path, self.config_path = folder/'pets_list.json', folder/'config.json'
        data = config_io.read_json(config_io.LIST_FILE)
        for entry in data['pets']:
            entry['enabled'] = entry['species'] == 'muuri'
            if entry['species'] == 'muuri':
                entry.update(size='Original', draggable=True, physics_enabled=False)
        self.list_path.write_text(json.dumps(data), encoding='utf-8')
        self.config_path.write_text('{"layer":"front"}', encoding='utf-8')
        self.patches = [patch.object(config_io, 'LIST_FILE', self.list_path),
                        patch.object(config_io, 'CONFIG_FILE', self.config_path),
                        patch.object(petworker, 'CONFIG_FILE', str(self.list_path)),
                        patch.object(windows_API, 'CONFIG_FILE', str(self.config_path))]
        for item in self.patches:
            item.start()
        self.window = MainWindow(self.app)
        self.assertTrue(self.window.start_refresh())
        self.stop_worker()
        self.window.drag_timer.stop()
        self.panel = self.window.panel

    def stop_worker(self):
        self.window.worker.stop()
        self.assertTrue(self.window.worker.wait(3000))

    def tearDown(self):
        self.window.shutdown()
        self.window.hide()
        self.window.deleteLater()
        self.app.processEvents()
        for item in reversed(self.patches):
            item.stop()
        self.folder.cleanup()

    def choose(self, species):
        self.panel.select(species)
        self.panel.activate_selected()

    def test_preview_eight_states_sizes_and_independent_speeds(self):
        before = self.list_path.read_bytes()
        self.panel.select('fefo')
        self.assertFalse(self.panel.is_dirty())
        self.assertEqual(self.panel.preview_state.count(), 8)
        self.assertEqual(self.panel.size.currentData(), 'Original')
        for index in range(8):
            self.panel.preview_state.setCurrentIndex(index)
            self.assertEqual(len(self.panel.preview.frames), 8)
            self.assertEqual(self.panel.preview.frames[0].height(), 128)
            self.assertEqual(self.panel.preview.frames[0].pixelColor(0,0).alpha(), 0)
        for size, height in [('Very Small',20), ('Small',40), ('Original',128),
                             ('Medium',125), ('Big',150), ('Really Big',200)]:
            self.panel.size.setCurrentIndex(self.panel.size.findData(size))
            self.assertEqual(self.panel.preview.frames[0].height(), height)
        self.panel.preview_state.setCurrentIndex(self.panel.preview_state.findData('walk'))
        velocity, fps = self.panel.preview.velocity, self.panel.preview.fps
        self.panel.animation.setValue(200)
        self.assertEqual(self.panel.preview.velocity, velocity)
        self.assertEqual(self.panel.preview.fps, fps*2)
        self.panel.movement.setValue(50)
        self.assertEqual(self.panel.preview.velocity, velocity/2)
        self.assertEqual(self.panel.preview.fps, fps*2)
        for state in ('idle', 'lie', 'swipe', 'drag', 'fly'):
            self.panel.preview_state.setCurrentIndex(self.panel.preview_state.findData(state))
            self.assertEqual(self.panel.preview.velocity, 0)
        self.assertEqual(self.list_path.read_bytes(), before)

    def test_apply_round_trip_persistence_and_no_duplicate_worker(self):
        old_pet = self.window.pets[0]
        old_worker, old_hwnd = self.window.worker, old_pet.hwnd
        before = self.list_path.read_bytes()
        self.choose('fefo')
        self.panel.physics.setChecked(True)
        self.panel.movement.setValue(150)
        self.panel.animation.setValue(175)
        self.assertEqual(self.list_path.read_bytes(), before)
        self.assertIs(self.window.pets[0], old_pet)
        self.assertTrue(self.panel.apply())
        self.stop_worker()
        self.assertFalse(old_worker.isRunning())
        self.assertFalse(win32gui.IsWindow(old_hwnd))
        self.assertEqual([p.species for p in self.window.pets], ['fefo'])
        pet = self.window.pets[0]
        self.assertEqual((pet.width,pet.height), (128,128))
        self.assertTrue(pet.draggable and pet.physics_enabled)
        self.assertEqual((pet.movement_multiplier,pet.animation_multiplier), (1.5,1.75))
        other = MainWindow(self.app)
        try:
            self.assertTrue(other.start_refresh())
            other.worker.stop(); self.assertTrue(other.worker.wait(3000))
            self.assertEqual([p.species for p in other.pets], ['fefo'])
            self.assertEqual(other.pets[0].animation_multiplier, 1.75)
        finally:
            other.shutdown(); other.deleteLater()
        self.choose('muuri')
        self.assertTrue(self.panel.apply())
        self.stop_worker()
        self.assertEqual([p.species for p in self.window.pets], ['muuri'])
        self.assertEqual(self.window.pets[0].height, 64)
        self.choose('fefo')
        self.assertEqual(self.panel.animation.value(), 175)
        self.assertTrue(self.panel.apply())
        self.stop_worker()
        self.assertEqual([p.species for p in self.window.pets], ['fefo'])

    def test_drag_flight_regrab_landing_restores_ground_state(self):
        self.choose('fefo')
        self.panel.physics.setChecked(True)
        self.assertTrue(self.panel.apply())
        self.stop_worker()
        pet = self.window.pets[0]
        info = pet.STATES_INFO['walk']
        ground = State('walk', info['gif'], hold=32, movement_speed=2, direction=-1)
        pet.state = ground
        pet.frame_animation()
        ground.counter = 7
        pet.y = pet.floor_y-200
        pet.dragging = True
        pet.drag_direction = -1
        pet.update_state()
        self.assertEqual(pet.state.name, 'drag')
        self.assertIs(pet.drag_previous_state, ground)
        pet.dragging = False
        pet.motion.vx = 100
        pet.update_state()
        self.assertEqual((pet.state.name, pet.state.direction), ('fly', 1))
        pet.current_frame = 3
        pet.motion.vx = -100
        pet.update_state()
        self.assertEqual((pet.state.direction, pet.current_frame), (-1, 3))
        pet.dragging = True
        pet.update_state()
        self.assertEqual(pet.state.name, 'drag')
        self.assertIs(pet.drag_previous_state, ground)
        pet.dragging = False
        pet.update_state()
        self.assertEqual(pet.state.name, 'fly')
        pet.y = pet.floor_y
        pet.update_state()
        self.assertIs(pet.state, ground)
        self.assertEqual(ground.counter, 7)
        self.assertIsNone(pet.drag_previous_state)
        for _ in range(100):
            self.assertNotIn(pet.random_state().name, ('drag', 'fly'))
        pet.physics_enabled = False
        pet.y = pet.floor_y-200
        pet.update_state()
        self.assertNotEqual(pet.state.name, 'fly')

    def test_muuri_retains_default_airborne_drag_and_species_fallback(self):
        pet = self.window.pets[0]
        self.assertEqual(pet.motion.profile, {})
        pet.physics_enabled = True
        pet.y = pet.floor_y-200
        pet.update_state()
        self.assertEqual(pet.state.name, 'drag')
        pet.y = pet.floor_y
        pet.update_state()
        self.assertNotEqual(pet.state.name, 'drag')
        pet.physics_profile = {'airborne_animation': 'missing'}
        pet.y = pet.floor_y-200
        pet.update_state()
        self.assertEqual(pet.state.name, 'drag')

    def test_native_states_drag_mirroring_gravity_and_throw(self):
        self.choose('fefo')
        self.panel.physics.setChecked(True)
        self.assertTrue(self.panel.apply())
        self.stop_worker()
        pet = self.window.pets[0]
        for size, height in [('Very Small',20), ('Small',40), ('Original',128),
                             ('Medium',125), ('Big',150), ('Really Big',200)]:
            pet.size = size
            pet.frame_animation()
            self.assertEqual(pet.height, height)
        pet.size = 'Original'
        for state in STATES:
            info = pet.STATES_INFO[state]
            pet.state = State(state, info['gif'], hold=info['hold'],
                              movement_speed=info['movement_speed'], speed_animation=info['speed_animation'])
            pet.frame_animation()
            self.assertEqual((pet.width,pet.height,pet.frame_count), (128,128,8))
            draw_pet_frame(pet, pet.frames[0])
        info = pet.STATES_INFO['walk']
        pet.state = State('walk', info['gif'], hold=info['hold'],
                          movement_speed=info['movement_speed'], speed_animation=info['speed_animation'])
        pet.movement_multiplier, pet.animation_multiplier = 1.5, 2
        pet.frame_animation()
        self.assertEqual(pet.frame_interval, pet.state_interval/2)
        base_interval = pet.state_interval
        pet.animation_multiplier = 0.5
        pet.frame_animation()
        self.assertEqual(pet.state_interval, base_interval)
        self.assertEqual(pet.frame_interval, base_interval*2)
        pet.x = 200
        pet.state.direction = 1
        pet.state.next(pet)
        self.assertEqual(pet.x, 200 + info['movement_speed']*1.5)
        for direction in (1,-1):
            pet.state.direction = direction
            pet.last_state_update, pet.last_update = 1000, 0
            pet.current_frame = 0
            rendered = []
            worker = petworker.PetWorker([pet])
            worker.frame_ready.connect(lambda p, frame: rendered.append(frame), QtCore.Qt.ConnectionType.DirectConnection)
            with patch.object(petworker.time, 'time', return_value=1000), \
                    patch.object(petworker.time, 'sleep', side_effect=lambda _: worker.stop()):
                worker.run()
            expected = pet.frames[0] if direction == 1 else pet.frames[0].transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            self.assertEqual(rendered[0].tobytes(), expected.tobytes())
        info = pet.STATES_INFO['idle']
        pet.state = State('idle', info['gif'], hold=1000)
        pet.frame_animation()
        pet.x, pet.y = 200, 100
        point = 20 | (20 << 16)
        with patch('deskpets.physics.time.monotonic', return_value=100):
            win32gui.SendMessage(pet.hwnd, win32con.WM_LBUTTONDOWN, 1, point)
        with patch('deskpets.physics.time.monotonic', return_value=100.05):
            windows_API.Windows.move_drag(pet, 280, 100)
        pet.update_state()
        self.assertEqual(pet.state.name, 'drag')
        self.assertEqual(pet.state.direction, 1)
        with patch('deskpets.physics.time.monotonic', return_value=100.08):
            windows_API.Windows.move_drag(pet, 240, 90)
        pet.update_state()
        self.assertEqual(pet.state.direction, -1)
        with patch('deskpets.physics.time.monotonic', return_value=100.09):
            windows_API.Windows.finish_press(pet, (240,90))
        self.assertNotEqual(pet.motion.vx, 0)
        self.assertLess(pet.motion.vy, 0)
        pet.update_state()
        self.assertEqual(pet.state.name, 'fly')
        pet.motion.stop()
        y = pet.y
        windows_API.Windows.update_physics(pet, 0.016)
        self.assertGreater(pet.y, y)
        for _ in range(500):
            windows_API.Windows.update_physics(pet, 0.016)
        self.assertEqual(pet.y, pet.floor_y)


if __name__ == '__main__':
    unittest.main()
