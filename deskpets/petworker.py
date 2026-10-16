import json
import math
import os
import time
import traceback

from PIL import Image
from PyQt6 import QtCore

from .pets import Pet
from .desktop import Desktop
from . import config_io

CONFIG_FILE = str(config_io.LIST_FILE)
FPS_DEFAULT = 8
SIZE_DEFAULT = "small"
MAX_PETS = 6


# def load_pets():
#     try:
#         with open(CONFIG_FILE, "r", encoding="utf-8") as f:
#             cfg = json.load(f)
#
#         pets = []
#         for entry in cfg.get("pets", []):
#             if not entry.get("enabled", True):
#                 continue
#             species = entry["species"]
#             fps = entry.get("fps", FPS_DEFAULT)
#             size = entry.get("size", SIZE_DEFAULT)
#             for color in entry.get("colors", []):
#                 pets.append(Pet(species, color, fps, size))
#         return pets
#     except Exception as e:
#         print(e)
#         traceback.print_exc()
#         return []

def load_pets():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        pets = []
        for entry in cfg.get("pets", []):
            if len(pets) >= MAX_PETS:
                break
            if not entry.get("enabled", True):
                continue
            species = entry["species"]
            fps = entry.get("fps", FPS_DEFAULT)
            size = entry.get("size", SIZE_DEFAULT)
            for key in ("movement_multiplier", "animation_multiplier"):
                value = entry.get(key, 1.0)
                if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0.5 <= value <= 2:
                    raise ValueError(f"Multiplicador inválido: {species} / {key}")
            count = entry.get("count", 1)
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                raise ValueError(f"Quantidade inválida: {species}")
            for color in entry.get("colors", []):
                for instance_index in range(min(count, MAX_PETS-len(pets))):
                    pet = Pet(species, color, fps, size, draggable=entry.get("draggable", False),
                              settings_clicks=entry.get("settings_clicks", 0),
                              movement_multiplier=entry.get("movement_multiplier", 1.0),
                              animation_multiplier=entry.get("animation_multiplier", 1.0),
                              physics_enabled=entry.get("physics_enabled", False))
                    pet.main_window = None
                    pet.instance_index = instance_index
                    pets.append(pet)
        if len(pets) > 1:
            offset = 0
            for pet in pets:
                span = max(1, pet.screen_width - pet.width + 1)
                pet.x = (pet.screen_width - pet.width - offset) % span
                pet.free_roam = True
                offset += pet.width + 16
        return pets
    except Exception as e:
        for pet in locals().get("pets", []):
            Desktop.close(pet)
        print(e)
        traceback.print_exc()
        raise



class PetWorker(QtCore.QThread):
    frame_ready = QtCore.pyqtSignal(object, object)  # pet, frame image

    def __init__(self, pets):
        try:
            super().__init__()
            self.pets = pets
            self.running = True
        except Exception as e:
            print(e)
            traceback.print_exc()

    def run(self):
        try:
            while self.running:
                now = time.time()
                for pet in self.pets:
                    # Simulation keeps its original cadence; only GIF playback
                    # uses the animation multiplier, preserving state durations.
                    if now - getattr(pet, "last_state_update", 0) >= pet.state_interval:
                        pet.last_state_update = now
                        pet.update_state()
                    if now - getattr(pet, "last_update", 0) >= pet.frame_interval:
                        pet.last_update = now
                        frame_idx = pet.current_frame
                        frame_image = pet.frames[frame_idx]
                        if pet.state.direction < 0:
                            frame_image = frame_image.transpose(Image.FLIP_LEFT_RIGHT)
                        self.frame_ready.emit(pet, frame_image)
                        pet.current_frame = (frame_idx + 1) % pet.frame_count
                time.sleep(0.01)
        except Exception as e:
            print(e)
            traceback.print_exc()

    def stop(self):
        self.running = False
