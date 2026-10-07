import math
import time


class ClickSequence:
    """Count completed clicks, never native double-click notifications."""

    def __init__(self, required=4):
        self.required = required
        self.reset()

    def reset(self):
        self.count = 0
        self.started_at = None
        self.press_point = None
        self.moved = False

    def press(self, point, now=None):
        now = time.monotonic() if now is None else now
        if self.started_at is None or now - self.started_at > 1.5:
            self.reset()
            self.started_at = now
        self.press_point = point
        self.moved = False

    def move(self, point):
        if self.press_point is not None and math.dist(point, self.press_point) > 6:
            self.moved = True
            self.count = 0
            self.started_at = None

    def release(self, point, now=None):
        now = time.monotonic() if now is None else now
        self.move(point)
        valid = (self.press_point is not None and not self.moved
                 and self.started_at is not None and now - self.started_at <= 1.5)
        self.press_point = None
        if not valid:
            self.reset()
            return False
        self.count += 1
        if self.count == self.required:
            self.reset()
            return True
        return False
