# The stochastic melody brain. On each Euclidean-gated hit, picks a scale
# degree and octave: how often it stays on the current chord's tones vs
# wanders the wider scale is `wildness`; the pitch also carries a slow
# random-walk drift (`accumulator`) so it wanders rather than jumping
# independently every note - OXI's "accumulator that changes a note's pitch
# over successive repetitions", simplified to one continuous drift value.
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
        self.register = 1.0      # 0..2: how many octaves the accumulator can roam
        self.accum_depth = 0.4   # 0..1: how strongly the accumulator nudges per note

        self._accum = 0.0
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
        self._accum = 0.0
        self._buffer = [None] * self.steps
        self.frozen = False

    def next_note(self, index, chord_degree):
        slot = index % self.steps
        if self.frozen:
            return self._buffer[slot]

        chord_tones = diatonic_triad(chord_degree)
        if self._rng.random() < (1.0 - self.wildness):
            # avoid random.choice() - not reliably present in CircuitPython's
            # trimmed-down random module
            degree = chord_tones[self._rng.randrange(len(chord_tones))]
        else:
            degree = self._rng.randrange(7)

        step = self._rng.uniform(-1.0, 1.0) * self.accum_depth
        self._accum += step
        span = max(self.register, 0.05)
        if self._accum > span:
            self._accum = span - (self._accum - span)
        elif self._accum < -span:
            self._accum = -span - (self._accum + span)
        octave = round(self._accum)

        result = (degree, octave)
        self._buffer[slot] = result
        return result

    def rest(self, index):
        # a Euclidean rest still clears that slot's buffer entry, so a
        # later freeze doesn't replay a stale note there
        self._buffer[index % self.steps] = None
