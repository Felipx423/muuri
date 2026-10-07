import math
import time
from collections import deque


class Motion:
    """Pixel/second motion, independent of GIF speed and animation states."""

    def __init__(self):
        self.samples = deque(maxlen=32)
        self.vx = 0.0
        self.vy = 0.0

    def begin(self, x, y, now=None):
        self.stop()
        self.track(x, y, now)

    def stop(self):
        self.vx = self.vy = 0.0
        self.samples.clear()

    def track(self, x, y, now=None):
        now = time.monotonic() if now is None else now
        if self.samples and now <= self.samples[-1][0]:
            return
        self.samples.append((now, x, y))
        while len(self.samples) > 1 and now-self.samples[0][0] > 0.12:
            self.samples.popleft()

    def launch(self, now=None):
        now = time.monotonic() if now is None else now
        if len(self.samples) >= 2 and now-self.samples[-1][0] <= 0.1:
            first, last = self.samples[0], self.samples[-1]
            elapsed = last[0]-first[0]
            if elapsed >= 0.008:
                self.vx = max(-1400, min(1400, (last[1]-first[1])/elapsed))
                self.vy = max(-1400, min(1400, (last[2]-first[2])/elapsed))
        self.samples.clear()

    def advance(self, pet, elapsed):
        if not pet.physics_enabled:
            self.stop()
            return False
        if pet.mouse_pressed or pet.dragging or pet.wall_scene_step is not None:
            return False
        if pet.settings_clicks and pet.click_sequence.count:
            if time.monotonic()-pet.click_sequence.started_at <= 1.5:
                return False
            pet.click_sequence.reset()
        elapsed = max(0, min(elapsed, 0.05))
        if not elapsed:
            return False
        before = pet.x, pet.y
        floor = max(0, min(pet.floor_y, pet.screen_height-pet.height))
        if pet.y >= floor and self.vy >= 0:
            pet.y = floor
            self.vy = 0
            self.vx *= math.exp(-12*elapsed)
        else:
            self.vy = min(1600, self.vy+1800*elapsed)
            pet.y += self.vy*elapsed
            self.vx *= math.exp(-1.6*elapsed)
            if pet.y >= floor:
                pet.y = floor
                self.vy = -self.vy*0.25 if self.vy > 140 else 0
        pet.x += self.vx*elapsed
        right = max(0, pet.screen_width-pet.width)
        if pet.x < 0 or pet.x > right:
            pet.x = max(0, min(pet.x, right))
            self.vx *= -0.35
        if pet.y < 0:
            pet.y = 0
            self.vy = abs(self.vy)*0.35
        if abs(self.vx) < 5:
            self.vx = 0
        pet.y_def = pet.y
        if abs(self.vx) >= 5:
            pet.free_roam = True
        return before != (pet.x, pet.y)
