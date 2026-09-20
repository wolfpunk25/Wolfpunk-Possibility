# Free-running internal clock. Provides three rates off one tempo:
#   - MIDI clock ticks (24 ppqn), for external gear to lock to
#   - beats (quarter notes), which advance the chord progression
#   - subticks (a configurable subdivision of the beat), which drive the
#     Euclidean melody grid
#
# The real OXI One has physical clock in/out jacks; the MacroPad has none,
# so this sends the same information out as USB MIDI clock/start/stop
# instead.

import time

PPQN = 24


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Clock:
    def __init__(self, bpm=100, subdivisions_per_beat=4):
        self.bpm = bpm
        self.subdivisions_per_beat = subdivisions_per_beat
        self.running = False
        self._next_midi_tick = 0.0
        self._next_beat = 0.0
        self._next_subtick = 0.0

    def set_bpm(self, bpm):
        self.bpm = _clamp(bpm, 40, 220)

    def set_subdivisions(self, n):
        self.subdivisions_per_beat = int(_clamp(n, 1, 8))

    def beat_seconds(self):
        return 60.0 / self.bpm

    def start(self):
        now = time.monotonic()
        self.running = True
        self._next_midi_tick = now
        self._next_beat = now
        self._next_subtick = now

    def stop(self):
        self.running = False

    def due_midi_ticks(self):
        if not self.running:
            return 0
        now = time.monotonic()
        interval = self.beat_seconds() / PPQN
        count = 0
        while now >= self._next_midi_tick:
            self._next_midi_tick += interval
            count += 1
        return count

    def due_beats(self):
        if not self.running:
            return 0
        now = time.monotonic()
        interval = self.beat_seconds()
        count = 0
        while now >= self._next_beat:
            self._next_beat += interval
            count += 1
        return count

    def due_subticks(self):
        if not self.running:
            return 0
        now = time.monotonic()
        interval = self.beat_seconds() / self.subdivisions_per_beat
        count = 0
        while now >= self._next_subtick:
            self._next_subtick += interval
            count += 1
        return count
