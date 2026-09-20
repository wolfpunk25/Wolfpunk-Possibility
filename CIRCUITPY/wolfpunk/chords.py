# A 4-slot diatonic chord loop - the harmonic reference the generative
# melody follows, the way the OXI One's chord sequencer anchors its other
# generative parts so they sound related rather than arbitrary.
#
# Each slot just holds a scale degree (0-6); scales.diatonic_triad() turns
# that into an actual chord. Advancing is beat-counted rather than tied to
# the melody's own Euclidean grid, so the harmony changes on a steady pulse
# regardless of how busy or sparse the melody is being.

DEFAULT_SLOTS = [0, 4, 5, 3]  # I - V - vi - IV, diatonic to whatever scale/root is active


class ChordProgression:
    def __init__(self):
        self.slots = list(DEFAULT_SLOTS)
        self.beats_per_chord = 4
        self.index = 0
        self._beat_count = 0
        self.laps = 0  # how many full cycles through the progression have completed

    def current_degree(self):
        return self.slots[self.index]

    def set_degree(self, slot, degree):
        self.slots[slot] = degree % 7

    def jump_to(self, slot):
        self.index = slot % len(self.slots)
        self._beat_count = 0

    def on_beat(self):
        """Call once per elapsed quarter note. Returns True if the chord
        just changed (so callers can react, e.g. resync the accumulator).
        A chord holds for a full `beats_per_chord` beats before advancing -
        the transition lands on the call *after* that count is reached, not
        on the one that reaches it, so a 4-beat chord actually gets all 4
        beats (0..3) rather than only 3."""
        self._beat_count += 1
        if self._beat_count > self.beats_per_chord:
            self._beat_count = 1
            self.index = (self.index + 1) % len(self.slots)
            if self.index == 0:
                self.laps += 1
            return True
        return False
