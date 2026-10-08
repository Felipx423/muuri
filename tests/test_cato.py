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
from deskpets.physics import Motion
from deskpets.state import State
from deskpets.window import MainWindow, draw_pet_frame


STATES = {'idle', 'walk', 'walk_fast', 'run', 'swipe', 'lie', 'drag'}


def rgba_pixels(image):
    raw = image.tobytes()
    return zip(raw[0::4],raw[1::4],raw[2::4],raw[3::4])


class CatoAssetTests(unittest.TestCase):
    def test_seven_128px_states_transparency_margins_and_distinct_cycles(self):
        data = PETS_DATA['cato']
        self.assertEqual(data['colors'], ['orange'])
        self.assertEqual(set(data['states']['orange']), STATES)
        cycles = {}
        for state, path in data['states']['orange'].items():
            with self.subTest(state=state), Image.open(config_io.BASE_DIR/path) as gif:
                self.assertEqual(gif.size, (128,128))
                self.assertEqual(gif.n_frames, 8)
                self.assertEqual(gif.info['loop'], 0)
                frames = []
                for i in range(8):
                    gif.seek(i)
                    frame = gif.convert('RGBA')
                    left,top,right,bottom = frame.getchannel('A').getbbox()
                    self.assertTrue(0 < left < right < 128 and 0 < top < bottom < 128)
                    self.assertEqual(frame.getpixel((0,0))[3], 0)
                    self.assertEqual(gif.disposal_method, 2)
                    self.assertEqual(gif.info['duration'], 120 if i%2 == 0 else 130)
                    pixels = list(rgba_pixels(frame))
                    self.assertGreater(sum(a == 255 and r > g*1.4 and g > b*1.2
                                           for r,g,b,a in pixels), 1200)
                    self.assertGreater(sum(a == 255 and r > 180 and g > 140 and b > 90
                                           for r,g,b,a in pixels), 200)
                    frames.append(frame.tobytes())
                self.assertGreater(len(set(frames)), 3)
                cycles[state] = b''.join(frames)
        self.assertEqual(len(set(cycles.values())), 7)

    def test_turquoise_fish_in_idle_lie_and_swipe(self):
        for state,path in PETS_DATA['cato']['states']['orange'].items():
            counts = []
            with Image.open(config_io.BASE_DIR/path) as gif:
                for i in range(gif.n_frames):
                    gif.seek(i)
                    counts.append(sum(a == 255 and r < 90 and g > 100 and b > 80 and g > r*1.6
                                      for r,g,b,a in rgba_pixels(gif.convert('RGBA'))))
            if state == 'swipe':
                self.assertGreater(max(counts), 40, 'The reference fishbone is missing')
            elif state in {'idle', 'lie'}:
                self.assertGreater(min(counts), 40, 'The reference fishbone must remain visible throughout the cycle')
            else:
                self.assertEqual(max(counts), 0, 'Fish or turquoise decorations leaked into a movement or drag state')


class CatoIntegrationTests(unittest.TestCase):
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
            if entry['species'] == 'cato':
                entry['custom_note'] = 'preserve'
        self.list_path.write_text(json.dumps(data), encoding='utf-8')
        self.config_path.write_text('{"layer":"front"}', encoding='utf-8')
        self.patches = [patch.object(config_io,'LIST_FILE',self.list_path),
                        patch.object(config_io,'CONFIG_FILE',self.config_path),
                        patch.object(petworker,'CONFIG_FILE',str(self.list_path)),
                        patch.object(windows_API,'CONFIG_FILE',str(self.config_path))]
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

    def test_preview_seven_states_all_sizes_and_independent_speeds_without_saving(self):
        before = self.list_path.read_bytes()
        self.panel.select('cato')
        self.assertFalse(self.panel.is_dirty())
        self.assertEqual(self.panel.preview_state.count(), 7)
        self.assertEqual(self.panel.size.currentData(), 'Original')
        for state in STATES:
            self.panel.preview_state.setCurrentIndex(self.panel.preview_state.findData(state))
            self.assertEqual(len(self.panel.preview.frames), 8)
            self.assertEqual(self.panel.preview.frames[0].height(), 128)
            self.assertEqual(self.panel.preview.frames[0].pixelColor(0,0).alpha(), 0)
        for size,height in [('Very Small',20),('Small',40),('Original',128),
                            ('Medium',125),('Big',150),('Really Big',200)]:
            self.panel.size.setCurrentIndex(self.panel.size.findData(size))
            self.assertEqual(self.panel.preview.frames[0].height(), height)
        self.panel.preview_state.setCurrentIndex(self.panel.preview_state.findData('walk'))
        velocity,fps = self.panel.preview.velocity,self.panel.preview.fps
        self.panel.animation.setValue(200)
        self.assertEqual((self.panel.preview.velocity,self.panel.preview.fps), (velocity,fps*2))
        self.panel.movement.setValue(50)
        self.assertEqual((self.panel.preview.velocity,self.panel.preview.fps), (velocity/2,fps*2))
        for state in ('idle','lie','swipe','drag'):
            self.panel.preview_state.setCurrentIndex(self.panel.preview_state.findData(state))
            self.assertEqual(self.panel.preview.velocity, 0)
        self.assertEqual(self.list_path.read_bytes(), before)

    def test_apply_switches_muuri_cato_fefo_both_ways_and_persists(self):
        for species in ['cato','muuri','cato','fefo','cato','fefo','cato']:
            old_pet,old_worker = self.window.pets[0],self.window.worker
            old_hwnd = old_pet.hwnd
            self.choose(species)
            if species == 'cato':
                self.panel.physics.setChecked(True)
                self.panel.movement.setValue(150)
                self.panel.animation.setValue(175)
            self.assertIs(self.window.pets[0],old_pet)
            self.assertTrue(self.panel.apply())
            self.stop_worker()
            self.assertFalse(old_worker.isRunning())
            self.assertFalse(win32gui.IsWindow(old_hwnd))
            self.assertEqual([p.species for p in self.window.pets],[species])
            if species == 'cato':
                pet = self.window.pets[0]
                self.assertEqual((pet.height,pet.draggable,pet.physics_enabled),(128,True,True))
                self.assertEqual((pet.movement_multiplier,pet.animation_multiplier),(1.5,1.75))
        saved = next(e for e in config_io.read_json(self.list_path)['pets'] if e['species'] == 'cato')
        self.assertEqual(saved['custom_note'],'preserve')
        other = MainWindow(self.app)
        try:
            self.assertTrue(other.start_refresh())
            other.worker.stop()
            self.assertTrue(other.worker.wait(3000))
            pet = other.pets[0]
            self.assertEqual((pet.species,pet.size,pet.physics_enabled),('cato','Original',True))
            self.assertEqual((pet.movement_multiplier,pet.animation_multiplier),(1.5,1.75))
        finally:
            other.shutdown()
            other.deleteLater()

    def test_native_rendering_mirroring_and_drag_uses_ground_physics(self):
        self.choose('cato')
        self.panel.physics.setChecked(True)
        self.assertTrue(self.panel.apply())
        self.stop_worker()
        pet = self.window.pets[0]
        self.assertEqual(pet.motion.profile,{})
        self.assertNotIn('physics',PETS_DATA['cato'])
        self.assertNotIn('fly',pet.STATES_INFO)
        for state in STATES:
            info = pet.STATES_INFO[state]
            pet.state = State(state,info['gif'],hold=info['hold'],movement_speed=info['movement_speed'],
                              speed_animation=info['speed_animation'])
            pet.frame_animation()
            draw_pet_frame(pet,pet.frames[0])
            for direction in (1,-1):
                pet.state.direction = direction
                pet.last_state_update,pet.last_update,pet.current_frame = 1000,0,0
                rendered = []
                worker = petworker.PetWorker([pet])
                worker.frame_ready.connect(lambda p,f: rendered.append(f),QtCore.Qt.ConnectionType.DirectConnection)
                with patch.object(petworker.time,'time',return_value=1000), \
                        patch.object(petworker.time,'sleep',side_effect=lambda _: worker.stop()):
                    worker.run()
                expected = pet.frames[0] if direction == 1 else pet.frames[0].transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                self.assertEqual(rendered[0].tobytes(),expected.tobytes())
        ground = State('idle',pet.STATES_INFO['idle']['gif'],hold=1000)
        pet.state = ground
        pet.frame_animation()
        ground.counter = 5
        pet.x,pet.y = 200,100
        point = 20 | (20 << 16)
        with patch('deskpets.physics.time.monotonic',return_value=100):
            win32gui.SendMessage(pet.hwnd,win32con.WM_LBUTTONDOWN,1,point)
        with patch('deskpets.physics.time.monotonic',return_value=100.05):
            windows_API.Windows.move_drag(pet,280,100)
        pet.update_state()
        self.assertEqual((pet.state.name,pet.state.direction),('drag',1))
        with patch('deskpets.physics.time.monotonic',return_value=100.08):
            windows_API.Windows.move_drag(pet,240,90)
        pet.update_state()
        self.assertEqual(pet.state.direction,-1)
        with patch('deskpets.physics.time.monotonic',return_value=100.09):
            windows_API.Windows.finish_press(pet,(240,90))
        self.assertNotEqual(pet.motion.vx,0)
        self.assertLess(pet.motion.vy,0)
        pet.update_state()
        self.assertEqual(pet.state.name,'drag')
        bounced = False
        for _ in range(600):
            windows_API.Windows.update_physics(pet,1/60)
            bounced |= pet.motion.vy < 0 and pet.y == pet.floor_y
        self.assertTrue(bounced)
        pet.update_state()
        self.assertIs(pet.state,ground)
        self.assertEqual(ground.counter,5)
        self.assertEqual((pet.y,pet.motion.vy),(pet.floor_y,0))

    def test_cato_drop_matches_muuri_and_remains_distinct_from_fefo(self):
        from types import SimpleNamespace
        from deskpets.clicks import ClickSequence
        def body():
            return SimpleNamespace(physics_enabled=True,mouse_pressed=False,dragging=False,
                                   wall_scene_step=None,settings_clicks=0,click_sequence=ClickSequence(),
                                   x=400.,y=100.,y_def=100.,floor_y=600,screen_height=728,
                                   height=128,width=128,screen_width=2000,free_roam=True)
        motions = [Motion(PETS_DATA[s].get('physics')) for s in ['cato','muuri','fefo']]
        bodies = [body() for _ in motions]
        for _ in range(60):
            for motion,pet in zip(motions,bodies):
                motion.advance(pet,1/60)
            self.assertEqual((bodies[0].x,bodies[0].y,motions[0].vy),
                             (bodies[1].x,bodies[1].y,motions[1].vy))
        self.assertGreater(bodies[0].y,bodies[2].y+200)
        self.assertEqual(PETS_DATA['fefo']['physics']['airborne_animation'],'fly')


if __name__ == '__main__':
    unittest.main()
