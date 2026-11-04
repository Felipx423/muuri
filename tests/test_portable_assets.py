import unittest

from PIL import Image

from deskpets import config_io
from deskpets.pets import PETS_DATA
from deskpets.remove_alpha import GifHelper


class PortableAssetTests(unittest.TestCase):
    def test_all_custom_pet_cycles_load_with_same_canvas_and_opaque_character(self):
        for species in ('muuri','fefo','cato','manu','eco','voltinha','friguinho'):
            color = PETS_DATA[species]['colors'][0]
            for state,path in PETS_DATA[species]['states'][color].items():
                with self.subTest(species=species,state=state),Image.open(config_io.BASE_DIR/path) as gif:
                    frames = GifHelper.load_gif_frames(path)
                    self.assertEqual(len(frames),gif.n_frames)
                    self.assertTrue(frames)
                    self.assertTrue(all(f.mode=='RGBA' and f.size==gif.size for f in frames))
                    self.assertTrue(all(f.getchannel('A').getbbox() for f in frames))
