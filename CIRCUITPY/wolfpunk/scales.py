# Seven-degree scales, and diatonic triads built on top of them.
#
# A triad rooted at scale degree d is built by stacking thirds within the
# scale itself: degrees (d, d+2, d+4) mod 7. Because every scale here has
# exactly 7 degrees, this works generically for all of them and always
# stays inside the scale - no separate "chord quality" table needed.

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SCALES = {
    "Major":     [0, 2, 4, 5, 7, 9, 11],
    "Minor":     [0, 2, 3, 5, 7, 8, 10],
    "Dorian":    [0, 2, 3, 5, 7, 9, 10],
    "Byzantine": [0, 1, 4, 5, 7, 8, 10],  # Phrygian dominant
    "Lydian":    [0, 2, 4, 6, 7, 9, 11],
    "Mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "WholeTone": [0, 2, 4, 6, 8, 10, 12],
}

SCALE_NAMES = list(SCALES.keys())

BASE_MIDI = 48  # C3 - root note when ROOT index is 0 (C) and octave offset is 0


def midi_note(root_index, scale_name, degree, octave=0):
    offsets = SCALES[scale_name]
    degree_wrapped = degree % 7
    octave_carry = degree // 7  # let degree run past 6 and carry into the octave
    offset = offsets[degree_wrapped]
    return BASE_MIDI + root_index + offset + 12 * (octave + octave_carry)


def diatonic_triad(degree):
    """The three scale degrees (root, third, fifth) of the triad built on
    `degree`, stacking thirds within a 7-note scale."""
    return (degree % 7, (degree + 2) % 7, (degree + 4) % 7)
