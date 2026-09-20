# The monophonic voice: oscillator (tri/saw/square blend), resonant
# low-pass filter with a decay-only envelope driving its cutoff, and a
# drive stage that just pushes amplitude into synthio's own soft clipping.
# Previews the generative melody live through the onboard speaker, in
# parallel with the same notes going out over USB MIDI.
#
# Ported unchanged from the Wolfpunk Foam sister project, where this engine
# was built and debugged on this same MacroPad RP2040.
#
# IMPORTANT: a synthio.Note is built fresh on every trigger() rather than
# mutated and re-pressed. On this board's CircuitPython 10.2.1,
# Synthesizer.release_then_press() (and a manual release()+press() pair) on
# the *same* Note object plays once and then goes silent on every
# subsequent retrigger - confirmed on real hardware over serial REPL.
# Building a new Note each time and calling press() on it works reliably.
# Mutating an already-pressed note's own attributes (waveform/filter) while
# it keeps sounding is fine; it's specifically re-pressing the same object
# that's broken.

import time
import board
import audiopwmio
import synthio
import ulab.numpy as np

SAMPLE_RATE = 22050
TABLE_SIZE = 512
VOL = 28000

FILTER_MIN_HZ = 60
FILTER_MAX_HZ = 9000
ENV_FILTER_RANGE_HZ = 6000  # how far the envelope can swing the cutoff

ATTACK_TIME = 0.004
RELEASE_TIME = 0.03

WAVE_REGEN_THROTTLE = 0.03  # seconds; avoid rebuilding the table every tick


def _triangle():
    half = TABLE_SIZE // 2
    rising = [int(-VOL + (2 * VOL) * i / half) for i in range(half)]
    falling = [int(VOL - (2 * VOL) * i / half) for i in range(half)]
    return rising + falling


def _saw():
    return [int(VOL - (2 * VOL) * i / TABLE_SIZE) for i in range(TABLE_SIZE)]


def _pulse(width):
    on = max(1, min(TABLE_SIZE - 1, int(TABLE_SIZE * width)))
    return [VOL] * on + [-VOL] * (TABLE_SIZE - on)


def _crossfade(a, b, t):
    return [int(a[i] * (1 - t) + b[i] * t) for i in range(TABLE_SIZE)]


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Voice:
    def __init__(self, macropad):
        # adafruit_macropad.MacroPad already claims SPEAKER_ENABLE in its own
        # constructor and never exposes it publicly, so reuse the pin it's
        # holding rather than fight it for ownership (raises "in use").
        macropad._speaker_enable.value = True

        self.audio = audiopwmio.PWMAudioOut(board.SPEAKER)
        self.synth = synthio.Synthesizer(sample_rate=SAMPLE_RATE)
        self.audio.play(self.synth)

        self._tri = _triangle()
        self._saw = _saw()
        self._pulse_width = 0.5
        self._pulse = _pulse(self._pulse_width)
        self._blend = 0.35
        self._last_wave_regen = 0.0
        self._waveform = np.array(self._crossfaded(), dtype=np.int16)

        self.cutoff_base = 2000
        self.resonance = 1.2
        self.env_depth = 0.5  # -1..+1, negative = inverted per the manual's "eg inv"
        self.decay_time = 0.3
        self.drive = 0.15
        self.level = 0.7

        self.note = None
        self._note_on_time = None
        self._playing = False
        self._extra_filter_hz = 0.0
        self._current_decay_time = self.decay_time

    def _crossfaded(self):
        if self._blend <= 0.5:
            return _crossfade(self._tri, self._saw, self._blend * 2)
        return _crossfade(self._saw, self._pulse, (self._blend - 0.5) * 2)

    def set_wave(self, blend, pulse_width=None):
        now = time.monotonic()
        self._blend = _clamp(blend, 0.0, 1.0)
        if pulse_width is not None:
            self._pulse_width = _clamp(pulse_width, 0.05, 0.95)
        if now - self._last_wave_regen < WAVE_REGEN_THROTTLE:
            return
        self._last_wave_regen = now
        self._pulse = _pulse(self._pulse_width)
        self._waveform = np.array(self._crossfaded(), dtype=np.int16)

    def set_filter(self, cutoff_hz, resonance):
        self.cutoff_base = _clamp(cutoff_hz, FILTER_MIN_HZ, FILTER_MAX_HZ)
        self.resonance = _clamp(resonance, 0.5, 8.0)

    def set_envelope(self, decay_time, depth):
        self.decay_time = _clamp(decay_time, 0.005, 2.0)
        self.env_depth = _clamp(depth, -1.0, 1.0)

    def set_drive(self, drive, level):
        self.drive = _clamp(drive, 0.0, 1.0)
        self.level = _clamp(level, 0.15, 1.0)

    def _filter_for(self, elapsed):
        decay_frac = 2 ** (-elapsed / max(self._current_decay_time, 0.005))
        depth_hz = self.env_depth * ENV_FILTER_RANGE_HZ * decay_frac
        cutoff = self.cutoff_base + depth_hz + self._extra_filter_hz
        cutoff = _clamp(cutoff, FILTER_MIN_HZ, FILTER_MAX_HZ)
        # CircuitPython 10.2.1's synthio has no Synthesizer.low_pass_filter()
        # helper - build the Biquad directly instead.
        return synthio.Biquad(synthio.FilterMode.LOW_PASS, frequency=cutoff, Q=self.resonance)

    def trigger(self, midi_note, extra_filter_hz=0.0, accent=1.0, decay_scale=1.0):
        self._note_on_time = time.monotonic()
        self._playing = True
        self._extra_filter_hz = extra_filter_hz
        # per-note length: downbeats ring a little longer, busy off-beats
        # get clipped shorter, instead of every note lasting identically
        self._current_decay_time = _clamp(self.decay_time * decay_scale, 0.02, 2.5)

        amp = min(self.level * (1.0 + self.drive * 2.5) * accent, 3.0)
        envelope = synthio.Envelope(
            attack_time=ATTACK_TIME,
            decay_time=self._current_decay_time,
            sustain_level=0.0,
            release_time=RELEASE_TIME,
        )
        note = synthio.Note(
            frequency=synthio.midi_to_hz(midi_note),
            waveform=self._waveform,
            amplitude=amp,
            envelope=envelope,
            filter=self._filter_for(0.0),
        )
        self.synth.release_all()
        self.synth.press(note)
        self.note = note

    def silence(self):
        self.synth.release_all()
        self._playing = False

    def tick(self):
        """Call every main-loop iteration to sweep the filter envelope."""
        if not self._playing or self.note is None or self._note_on_time is None:
            return
        if abs(self.env_depth) < 0.01:
            return  # flat cutoff, nothing to sweep
        elapsed = time.monotonic() - self._note_on_time
        if elapsed > self._current_decay_time * 6:
            self._playing = False  # envelope has settled; stop polling
            return
        self.note.filter = self._filter_for(elapsed)
