"""Qt backend tests also run on Windows; Cocoa assertions run only on macOS."""
import collections
from ctypes import c_void_p
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
from PyQt6 import QtCore, QtGui, QtWidgets

from deskpets import config_io, macos_api, pets, petworker, remove_alpha, window
from deskpets.state import State


class MacOSBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = Path(self.folder.name)
        data = json.loads((config_io.BASE_DIR/'pets_list.json').read_text(encoding='utf-8'))
        for entry in data['pets']:
            entry.update(enabled=entry['species']=='muuri',count=1,size='Original',
                         movement_multiplier=1.,animation_multiplier=1.,draggable=True,physics_enabled=False)
        self.list_path, self.config_path = root/'pets_list.json', root/'config.json'
        self.list_path.write_text(json.dumps(data),encoding='utf-8')
        self.config_path.write_text('{"layer":"front"}',encoding='utf-8')
        self.patches = [patch.object(config_io,'LIST_FILE',self.list_path),
                        patch.object(config_io,'CONFIG_FILE',self.config_path),
                        patch.object(petworker,'CONFIG_FILE',str(self.list_path)),
                        patch.object(pets,'Desktop',macos_api.MacOS),
                        patch.object(petworker,'Desktop',macos_api.MacOS),
                        patch.object(window,'Desktop',macos_api.MacOS),
                        patch.object(window,'IS_WINDOWS',False),
                        patch.object(remove_alpha,'sys',SimpleNamespace(platform='darwin')),
                        patch.object(macos_api,'screen_rect',return_value=QtCore.QRect(40,25,1400,900))]
        for item in self.patches:
            item.start()
        self.owner = window.MainWindow(self.app)
        self.assertTrue(self.owner.start_refresh())
        self.stop_worker()
        self.owner.drag_timer.stop()
        self.pet = self.owner.pets[0]
        self.pet.state = State('idle',self.pet.STATES_INFO['idle']['gif'],hold=1000)
        self.pet.frame_animation()
        self.pet.x, self.pet.y, self.pet.y_def = 250,150,150
        self.pet.hwnd.place(250,150)
        self.app.processEvents()

    def stop_worker(self):
        self.owner.worker.stop()
        self.assertTrue(self.owner.worker.wait(3000))

    def tearDown(self):
        self.owner.shutdown()
        self.owner.hide()
        self.owner.deleteLater()
        self.app.processEvents()
        for item in reversed(self.patches):
            item.stop()
        self.folder.cleanup()

    def send(self, kind, local=(30,30), global_point=None):
        view = self.pet.hwnd
        point = QtCore.QPoint(*local)
        global_point = global_point or view.mapToGlobal(point)
        release = kind == QtCore.QEvent.Type.MouseButtonRelease
        move = kind == QtCore.QEvent.Type.MouseMove
        event = QtGui.QMouseEvent(kind,QtCore.QPointF(point),QtCore.QPointF(global_point),
                                 QtCore.Qt.MouseButton.NoButton if move else QtCore.Qt.MouseButton.LeftButton,
                                 QtCore.Qt.MouseButton.NoButton if release else QtCore.Qt.MouseButton.LeftButton,
                                 QtCore.Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(view,event)

    def test_translucency_upright_rgba_mask_and_menu_bar_actions(self):
        view = self.pet.hwnd
        self.assertTrue(view.testAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(view.windowFlags() & QtCore.Qt.WindowType.WindowDoesNotAcceptFocus)
        self.assertTrue(view.testAttribute(QtCore.Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow))
        self.assertEqual((view.x(),view.y()), (290,175))
        source = config_io.BASE_DIR/self.pet.STATES_INFO['idle']['gif']
        with Image.open(source) as gif:
            self.assertEqual(remove_alpha.GifHelper.load_gif_frames(str(source))[0].tobytes(),gif.convert('RGBA').tobytes())
        for name, info in self.pet.STATES_INFO.items():
            self.pet.state = State(name,info['gif'])
            self.pet.frame_animation()
            for frame in self.pet.frames:
                macos_api.MacOS.draw_pet_frame(self.pet,frame)
                self.assertEqual(view.frame.size(),QtCore.QSize(self.pet.width,self.pet.height))
                self.assertEqual(view.frame.pixelColor(0,0).alpha(),0)
                self.assertFalse(view.mask().contains(QtCore.QPoint(0,0)))
        actions = self.owner.tray_icon.contextMenu().actions()
        self.assertIn('Abrir configurações',[a.text() for a in actions])
        self.assertIn('Sair',[a.text() for a in actions])
        self.assertEqual(self.owner.quit_action.menuRole(),QtGui.QAction.MenuRole.QuitRole)

    def test_four_clicks_with_drag_disabled_and_double_click_counts_once(self):
        self.pet.draggable = False
        for index in range(4):
            kind = QtCore.QEvent.Type.MouseButtonPress if index%2==0 else QtCore.QEvent.Type.MouseButtonDblClick
            self.send(kind)
            self.send(QtCore.QEvent.Type.MouseButtonDblClick)
            self.send(QtCore.QEvent.Type.MouseButtonRelease)
            # Losing capture after a completed click must not clear the sequence.
            self.app.sendEvent(self.pet.hwnd,QtCore.QEvent(QtCore.QEvent.Type.UngrabMouse))
            self.app.processEvents()
            self.assertEqual(self.owner.isVisible(),index==3)
        self.assertEqual(self.owner.panel.species,'muuri')

    def test_native_mouse_drag_toss_and_regrab_share_terrestrial_physics(self):
        self.pet.physics_enabled = True
        destination = self.pet.hwnd.mapToGlobal(QtCore.QPoint(-10,10))
        with patch('deskpets.physics.time.monotonic',return_value=100):
            self.send(QtCore.QEvent.Type.MouseButtonPress)
        with patch('deskpets.physics.time.monotonic',return_value=100.04):
            self.send(QtCore.QEvent.Type.MouseMove,global_point=destination)
        self.pet.update_state()
        self.assertEqual(self.pet.state.name,'drag')
        self.assertEqual((self.pet.x,self.pet.y),(210,130))
        with patch('deskpets.physics.time.monotonic',return_value=100.05):
            self.send(QtCore.QEvent.Type.MouseButtonRelease,global_point=destination)
        self.assertLess(self.pet.motion.vx,0)
        self.assertLess(self.pet.motion.vy,0)
        self.assertEqual(self.pet.click_sequence.count,0)
        self.assertFalse(self.pet.mouse_pressed)
        macos_api.MacOS.update_physics(self.pet,.02)
        self.assertEqual((self.pet.hwnd.x(),self.pet.hwnd.y()),(round(self.pet.x)+40,round(self.pet.y)+25))
        self.send(QtCore.QEvent.Type.MouseButtonPress)
        self.assertEqual((self.pet.motion.vx,self.pet.motion.vy),(0,0))
        self.app.sendEvent(self.pet.hwnd,QtCore.QEvent(QtCore.QEvent.Type.UngrabMouse))
        self.assertFalse(self.pet.mouse_pressed)

    def test_multiple_copies_apply_persist_preserve_positions_and_remove(self):
        panel = self.owner.panel
        before = self.list_path.read_bytes()
        for species,count in [('manu',2),('fefo',1),('cato',1)]:
            panel.select(species)
            panel.activate_selected()
            panel.quantity.setText(str(count))
        panel.physics.setChecked(True)
        self.assertEqual(self.list_path.read_bytes(),before)
        with patch.object(petworker.PetWorker,'run',lambda worker: None):
            old_worker = self.owner.worker
            self.assertTrue(panel.apply())
            self.stop_worker()
            self.assertFalse(old_worker.isRunning())
            self.assertEqual(collections.Counter(p.species for p in self.owner.pets),
                             {'muuri':1,'manu':2,'fefo':1,'cato':1})
            copies = [p for p in self.owner.pets if p.species=='manu']
            for index,pet in enumerate(copies):
                pet.x,pet.y,pet.y_def = 150+index*180,200+index*30,200+index*30
            panel.select('fefo')
            panel.enabled.setChecked(False)
            self.assertTrue(panel.apply())
            self.stop_worker()
            copies = [p for p in self.owner.pets if p.species=='manu']
            self.assertEqual([(p.x,p.y) for p in copies],[(150,200),(330,230)])
            self.assertNotIn('fefo',[p.species for p in self.owner.pets])
            other = window.MainWindow(self.app)
            try:
                self.assertTrue(other.start_refresh())
                other.worker.stop()
                self.assertTrue(other.worker.wait(3000))
                self.assertEqual(collections.Counter(p.species for p in other.pets),
                                 {'muuri':1,'manu':2,'cato':1})
            finally:
                other.shutdown()
                other.deleteLater()

    def test_fefo_keeps_flight_profile_and_all_preview_sizes(self):
        self.owner.panel.select('fefo')
        self.owner.panel.activate_selected()
        self.owner.panel.physics.setChecked(True)
        self.assertTrue(self.owner.panel.apply())
        self.stop_worker()
        fefo = next(p for p in self.owner.pets if p.species=='fefo')
        fefo.y = fefo.floor_y-200
        fefo.update_state()
        self.assertEqual(fefo.state.name,'fly')
        self.assertEqual(fefo.motion.profile['gravity'],420)
        for size,height in [('Very Small',20),('Small',40),('Original',128),('Medium',125),('Big',150),('Really Big',200)]:
            panel = self.owner.panel
            panel.size.setCurrentIndex(panel.size.findData(size))
            self.assertEqual(panel.preview.frames[0].height(),height)

    @unittest.skipUnless(sys.platform=='darwin','Cocoa policy needs a real Mac')
    def test_cocoa_spaces_level_and_inactive_visibility(self):
        import AppKit
        import objc
        for layer in ('front', 'back'):
            with self.subTest(layer=layer):
                self.config_path.write_text(json.dumps({'layer':layer}),encoding='utf-8')
                self.assertTrue(self.owner.start_refresh())
                self.stop_worker()
                view = self.owner.pets[0].hwnd
                self.assertFalse(view.windowFlags() & QtCore.Qt.WindowType.WindowStaysOnTopHint)
                view.hide()
                view.show()
                self.app.processEvents()
                native = objc.objc_object(c_void_p=c_void_p(int(view.winId()))).window()
                self.assertEqual(native.level(),AppKit.NSStatusWindowLevel)
                self.assertFalse(native.hidesOnDeactivate())
                self.assertTrue(native.collectionBehavior() & AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces)


class MacOSImportTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform=='darwin','Checks actual macOS module loading')
    def test_application_imports_without_win32(self):
        code = "import sys; import deskpets.main; assert 'win32gui' not in sys.modules; assert 'deskpets.windows_API' not in sys.modules"
        subprocess.run([sys.executable,'-c',code],check=True,timeout=30)
