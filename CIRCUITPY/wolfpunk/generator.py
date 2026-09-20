# The stochastic melody brain. On each Euclidean-gated hit, picks a scale
# degree and octave: how often it stays on the current chord's tones vs
# wanders the wider scale is `wildness`.
#
# Pitch choice is a constrained melodic random walk, not independent random
# notes: each new note is the chosen-tone-set's *nearest* member to a target
# a small step away from the previous note (`accum_depth` controls how big
# that step tends to be), so the line moves mostly by step with occasional
# leaps instead of jumping around the whole register every hit - degree and
# octave used to be chosen independently of each other and of the previous
# note, which is what made it sound aimless rather than melodic.
#
# FREEZE is implemented as a ring buffer of the last full lap: while frozen,
# next_note() replays from the buffer instead of drawing new randomness, so
# whatever was playing keeps repeating exactly.

import random

from wolfpunk.scales import diatonic_triad


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Generator:
    def __init__(self, steps=16, seed=1):
        random.seed(seed)
        self._rng = random
        self.steps = steps
        self.wildness = 0.35     # 0..1: chord tones only -> full scale
        self.register = 1.0      # 0..2: how many octaves the line can roam from center
        self.accum_depth = 0.35  # 0..1: how big a melodic step tends to be

        self._last_pos = 0  # diatonic step position (octave*7 + degree) of the last note
        self.frozen = False
        self._buffer = [None] * steps  # index -> (degree, octave) or None

    def resize(self, steps):
        if steps == self.steps:
            return
        buf = [None] * steps
        for i in range(min(steps, self.steps)):
            buf[i] = self._buffer[i]
        self._buffer = buf
        self.steps = steps

    def reroll(self, seed=None):
        self._rng.seed(seed if seed is not None else self._rng.randrange(1000000))
        self._last_pos = 0
        self._buffer = [None] * self.steps
        self.frozen = False

    def _nearest(self, candidates, target):
        base_oct = round(target / 7)
        best_deg, best_pos, best_dist = candidates[0], None, None
        for deg in candidates:
            for oct_try in (base_oct - 1, base_oct, base_oct + 1):
                pos = oct_try * 7 + deg
                dist = abs(pos - target)
                if best_dist is None or dist < best_dist:
                    best_deg, best_pos, best_dist = deg, pos, dist
        return best_deg, best_pos

    def next_note(self, index, chord_degree):
        slot = index % self.steps
        if self.frozen:
            return self._buffer[slot]

        chord_tones = diatonic_triad(chord_degree)
        use_scale = self._rng.random() < self.wildness
        candidates = list(range(7)) if use_scale else list(chord_tones)

        # a triangular-ish spread (sum of two uniforms) favours small
        # melodic steps with occasional bigger leaps, closer to how real
        # melodies move than a flat random range would
        step_range = 1.0 + self.accum_depth * 6.0
        step = (self._rng.uniform(-1.0, 1.0) + self._rng.uniform(-1.0, 1.0)) * 0.5 * step_range
        target = self._last_pos + step

        # keep the overall register from drifting off forever by gently
        # pulling the target back toward home before snapping to a note
        span = max(self.register, 0.2) * 7.0
        target = _clamp(target, -span, span)

        degree, pos = self._nearest(candidates, target)
        self._last_pos = pos
        octave = pos // 7

        result = (degree, octave)
        self._buffer[slot] = result
        return result

    def rest(self, index):
        # a Euclidean rest still clears that slot's buffer entry, so a
        # later freeze doesn't replay a stale note there
        self._buffer[index % self.steps] = None
