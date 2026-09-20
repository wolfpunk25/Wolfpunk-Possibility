# Wolfpunk Possibility - a small, simple generative melody sequencer for
# the Adafruit MacroPad RP2040, loosely modelled on the OXI One MKII: a
# chord loop sets the harmony, and a stochastic melody follows it while
# continuously drifting. See docs/oxi-one-notes.md for the full mapping
# from the real instrument's ideas onto this one's keys/pages.

import time
from adafruit_macropad import MacroPad
from adafruit_midi.timing_clock import TimingClock
from adafruit_midi.start import Start
from adafruit_midi.stop import Stop
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff

from wolfpunk.voice import Voice
from wolfpunk.clock import Clock
from wolfpunk.chords import ChordProgression
from wolfpunk.generator import Generator
from wolfpunk.euclid import euclidean_rhythm
from wolfpunk.scales import SCALE_NAMES, NOTE_NAMES, midi_note
import wolfpunk.ui as ui_mod

MIDI_CHANNEL = 0  # channel 1
VELOCITY = 100
PHRASE_LAPS = 2  # laps through the 4-chord loop per phrase, before it breathes

PAGES = ["WILDNESS", "DENSITY", "ACCUM", "WAVE", "FILTER", "ENV", "DRIVE", "TEMPO", "SCALE"]


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class App:
    def __init__(self):
        self.macropad = MacroPad(midi_out_channel=MIDI_CHANNEL + 1)
        self.voice = Voice(self.macropad)
        self.clock = Clock(bpm=100)
        self.chords = ChordProgression()
        self.generator = Generator(steps=16)
        self.ui = ui_mod.UI(self.macropad)

        self.midi = self.macropad.midi

        self.page_index = 0
        self.shift_held = False
        self.held_chord_key = None

        self.wave_blend = 0.35
        self.wave_pw = 0.5
        self.filter_cutoff = 2000
        self.filter_res = 1.2
        self.env_decay = 0.3
        self.env_depth = 0.5
        self.drive = 0.15
        self.level = 0.7
        self.scale_index = 0
        self.root_index = 0

        self.steps = 16
        self.hits = 5
        self._euclid = euclidean_rhythm(self.steps, self.hits)

        self.octave_offset = 0
        self.muted = False
        self.sub_counter = 0
        self._last_tap = None

        self.last_midi_note = None
        self._push_all_params()
        self._last_render = 0.0
        self._flash_text = ""
        self._flash_until = 0.0

    # -- parameter push-through --------------------------------------
    def _push_all_params(self):
        self.voice.set_wave(self.wave_blend, self.wave_pw)
        self.voice.set_filter(self.filter_cutoff, self.filter_res)
        self.voice.set_envelope(self.env_decay, self.env_depth)
        self.voice.set_drive(self.drive, self.level)
        self.clock.set_bpm(self.clock.bpm)

    def _recompute_euclid(self):
        self.generator.resize(self.steps)
        self.hits = min(self.hits, self.steps)
        self._euclid = euclidean_rhythm(self.steps, self.hits)

    # -- encoder handling ----------------------------------------------
    def handle_encoder(self, delta):
        if delta == 0:
            return
        if self.held_chord_key is not None:
            slot = self.held_chord_key
            self.chords.set_degree(slot, self.chords.slots[slot] + delta)
            return

        page = PAGES[self.page_index]
        if page == "WILDNESS":
            if self.shift_held:
                self.generator.register = clamp(self.generator.register + delta * 0.05, 0.0, 2.0)
            else:
                self.generator.wildness = clamp(self.generator.wildness + delta * 0.02, 0.0, 1.0)
        elif page == "DENSITY":
            if self.shift_held:
                self.steps = int(clamp(self.steps + delta * 4, 8, 32))
                self._recompute_euclid()
            else:
                self.hits = int(clamp(self.hits + delta, 0, self.steps))
                self._euclid = euclidean_rhythm(self.steps, self.hits)
        elif page == "ACCUM":
            if self.shift_held:
                self.chords.beats_per_chord = int(clamp(self.chords.beats_per_chord + delta, 1, 8))
            else:
                self.generator.accum_depth = clamp(self.generator.accum_depth + delta * 0.02, 0.0, 1.0)
        elif page == "WAVE":
            if self.shift_held:
                self.wave_pw = clamp(self.wave_pw + delta * 0.02, 0.05, 0.95)
            else:
                self.wave_blend = clamp(self.wave_blend + delta * 0.02, 0.0, 1.0)
            self.voice.set_wave(self.wave_blend, self.wave_pw)
        elif page == "FILTER":
            if self.shift_held:
                self.filter_res = clamp(self.filter_res + delta * 0.1, 0.5, 8.0)
            else:
                self.filter_cutoff = clamp(self.filter_cutoff * (1.05 ** delta), 60, 9000)
            self.voice.set_filter(self.filter_cutoff, self.filter_res)
        elif page == "ENV":
            if self.shift_held:
                self.env_depth = clamp(self.env_depth + delta * 0.05, -1.0, 1.0)
            else:
                self.env_decay = clamp(self.env_decay * (1.08 ** delta), 0.005, 2.0)
            self.voice.set_envelope(self.env_decay, self.env_depth)
        elif page == "DRIVE":
            if self.shift_held:
                self.level = clamp(self.level + delta * 0.02, 0.15, 1.0)
            else:
                self.drive = clamp(self.drive + delta * 0.02, 0.0, 1.0)
            self.voice.set_drive(self.drive, self.level)
        elif page == "TEMPO":
            if self.shift_held:
                self.clock.set_subdivisions(self.clock.subdivisions_per_beat + delta)
            else:
                self.clock.set_bpm(self.clock.bpm + delta)
        elif page == "SCALE":
            if self.shift_held:
                self.root_index = (self.root_index + delta) % 12
            else:
                self.scale_index = (self.scale_index + delta) % len(SCALE_NAMES)

    # -- MIDI helpers -----------------------------------------------
    def _midi_note_on(self, note, velocity=VELOCITY):
        if self.last_midi_note is not None:
            self.midi.send(NoteOff(self.last_midi_note, 0))
        self.midi.send(NoteOn(note, velocity))
        self.last_midi_note = note

    def _midi_note_off(self):
        if self.last_midi_note is not None:
            self.midi.send(NoteOff(self.last_midi_note, 0))
            self.last_midi_note = None

    # -- generative core -----------------------------------------------
    def _metric_weights(self, index):
        """How strongly this subtick should lean toward chord tones
        (wildness_scale), how loud it should land (accent), how long the
        note should ring (decay_scale), and how strongly it should lean
        toward the *next* chord instead (resolve) - based on where it
        falls in the beat/chord grid. Real melodies favour chord tones and
        land harder/longer on strong beats, and lean into the next chord
        as the current one runs out, rather than treating every
        subdivision identically and changing chords abruptly."""
        subdiv = max(self.clock.subdivisions_per_beat, 1)
        chord_span = subdiv * max(self.chords.beats_per_chord, 1)
        pos_in_chord = index % chord_span

        last_beat_start = chord_span - subdiv
        if pos_in_chord >= last_beat_start:
            progress = (pos_in_chord - last_beat_start + 1) / subdiv  # 1/subdiv .. 1.0
            resolve = 0.25 + 0.55 * progress
        else:
            resolve = 0.0

        if pos_in_chord == 0:
            return 0.15, 1.0, 1.3, resolve  # downbeat: mostly chord tones, full accent, longest note
        if index % subdiv == 0:
            return 0.5, 0.8, 1.0, resolve  # other beat starts: moderate lean/accent, normal length
        return 1.0, 0.55, 0.6, resolve  # off-beat: full wildness, quieter, shorter

    def _phrase_breathing(self):
        """True while we're in the last chord of a phrase (every
        PHRASE_LAPS laps through the loop) - the bar that thins out and
        leans hard into the turnaround back to the tonic, like a phrase
        taking a breath before a cadence rather than running on forever."""
        last_slot = len(self.chords.slots) - 1
        return self.chords.laps % PHRASE_LAPS == PHRASE_LAPS - 1 and self.chords.index == last_slot

    def _on_subtick(self, index):
        chord_degree = self.chords.current_degree()
        next_chord_degree = self.chords.slots[(self.chords.index + 1) % len(self.chords.slots)]
        wildness_scale, accent, decay_scale, resolve = self._metric_weights(index)
        breathing = self._phrase_breathing()

        if self.generator.frozen:
            result = self.generator.next_note(index, chord_degree)
        else:
            hit = self._euclid[index % len(self._euclid)]
            subdiv = max(self.clock.subdivisions_per_beat, 1)
            if breathing:
                if hit and index % subdiv != 0:
                    hit = False  # thin to just the beat pulse during the breath
                resolve = min(1.0, resolve + 0.3)  # lean harder into the coming tonic
                decay_scale *= 1.4  # let the breath's notes ring longer, more relaxed
            if hit:
                result = self.generator.next_note(
                    index,
                    chord_degree,
                    wildness_scale=wildness_scale,
                    next_chord_degree=next_chord_degree,
                    resolve=resolve,
                )
            else:
                self.generator.rest(index)
                result = None

        if result is None:
            return
        degree, octave = result
        scale_name = SCALE_NAMES[self.scale_index]
        note = midi_note(self.root_index, scale_name, degree, octave=octave + self.octave_offset)
        note = int(clamp(note, 0, 127))
        if not self.muted:
            self.voice.trigger(note, accent=accent, decay_scale=decay_scale)
            velocity = int(clamp(VELOCITY * accent, 20, 127))
            self._midi_note_on(note, velocity)

    # -- key handling ---------------------------------------------------
    def handle_key(self, key_number, pressed):
        if key_number in ui_mod.KEY_CHORDS:
            if pressed:
                self.held_chord_key = key_number
                self.chords.jump_to(key_number)
            else:
                if self.held_chord_key == key_number:
                    self.held_chord_key = None
            return

        if not pressed and key_number != ui_mod.KEY_PAGE:
            return

        if key_number == ui_mod.KEY_OCT_DOWN:
            self.octave_offset = int(clamp(self.octave_offset - 1, -3, 3))
        elif key_number == ui_mod.KEY_OCT_UP:
            self.octave_offset = int(clamp(self.octave_offset + 1, -3, 3))
        elif key_number == ui_mod.KEY_FREEZE:
            self._toggle_freeze()
        elif key_number == ui_mod.KEY_REROLL:
            self._reroll()
        elif key_number == ui_mod.KEY_MUTE:
            self.muted = not self.muted
            if self.muted:
                self.voice.silence()
                self._midi_note_off()
        elif key_number == ui_mod.KEY_PLAY:
            self._toggle_run()
        elif key_number == ui_mod.KEY_TAP:
            self._handle_tap()
        elif key_number == ui_mod.KEY_PAGE:
            self.shift_held = pressed
            if pressed:
                self.page_index = (self.page_index + 1) % len(PAGES)

    def _handle_tap(self):
        now = time.monotonic()
        if self._last_tap is not None and (now - self._last_tap) < 2.0:
            interval = now - self._last_tap
            self.clock.set_bpm(60.0 / interval)
        self._last_tap = now

    def _toggle_run(self):
        if self.clock.running:
            self.clock.stop()
            self.voice.silence()
            self._midi_note_off()
            self.midi.send(Stop())
        else:
            self.clock.start()
            self.midi.send(Start())

    def handle_encoder_switch(self, held_ms):
        # a clicky button can easily take longer than expected to press and
        # release, so give a generous margin before treating it as a
        # deliberate long-press rather than a quick click
        if held_ms > 900:
            self._toggle_freeze()
        else:
            self._reroll()

    def _reroll(self):
        self.generator.reroll()
        self._flash("REROLL")

    def _toggle_freeze(self):
        self.generator.frozen = not self.generator.frozen
        self._flash("FROZEN" if self.generator.frozen else "UNFROZEN")

    def _flash(self, text):
        self._flash_text = text
        self._flash_until = time.monotonic() + 0.3

    # -- display ----------------------------------------------------
    def _render(self):
        page = PAGES[self.page_index]
        if page == "WILDNESS":
            primary = f"wild {self.generator.wildness:.2f}"
            secondary = f"range {self.generator.register:.2f}"
        elif page == "DENSITY":
            primary = f"hits {self.hits}/{self.steps}"
            secondary = f"steps {self.steps}"
        elif page == "ACCUM":
            primary = f"accum {self.generator.accum_depth:.2f}"
            secondary = f"beats/chord {self.chords.beats_per_chord}"
        elif page == "WAVE":
            primary = f"blend {self.wave_blend:.2f}"
            secondary = f"pw {self.wave_pw:.2f}"
        elif page == "FILTER":
            primary = f"cut {int(self.filter_cutoff)}Hz"
            secondary = f"res {self.filter_res:.2f}"
        elif page == "ENV":
            primary = f"decay {self.env_decay:.2f}s"
            secondary = f"depth {self.env_depth:+.2f}"
        elif page == "DRIVE":
            primary = f"drive {self.drive:.2f}"
            secondary = f"level {self.level:.2f}"
        elif page == "TEMPO":
            primary = f"{int(self.clock.bpm)} bpm"
            secondary = f"subdiv {self.clock.subdivisions_per_beat}"
        else:  # SCALE
            primary = SCALE_NAMES[self.scale_index]
            secondary = NOTE_NAMES[self.root_index]

        page_line = f"[{page}] {secondary}" if self.shift_held else f"{page}: {primary}"
        root_name = NOTE_NAMES[self.root_index]
        scale_name = SCALE_NAMES[self.scale_index]
        transport = "RUN" if self.clock.running else "STOP"
        status_line = f"{int(self.clock.bpm)}bpm {root_name}{scale_name} {transport}"
        flashing = time.monotonic() < self._flash_until
        flags = (
            (f"{self._flash_text} " if flashing else "")
            + ("FRZ " if self.generator.frozen else "")
            + ("MUT" if self.muted else "")
        )
        info_line = f"oct{self.octave_offset:+d} {self.hits}/{self.steps} {flags}"

        self.ui.render(page_line, status_line, info_line, self.chords.slots, self.chords.index)
        self.ui.leds(
            self.chords.slots,
            self.chords.index,
            self.clock.running,
            self.generator.frozen,
            self.muted,
            self.shift_held,
            flash=flashing,
        )

    # -- main loop --------------------------------------------------
    def run(self):
        macropad = self.macropad
        prev_encoder = macropad.encoder
        encoder_switch_down_at = None

        while True:
            while True:
                event = macropad.keys.events.get()
                if event is None:
                    break
                self.handle_key(event.key_number, event.pressed)

            enc = macropad.encoder
            if enc != prev_encoder:
                self.handle_encoder(enc - prev_encoder)
                prev_encoder = enc

            self.macropad.encoder_switch_debounced.update()
            if self.macropad.encoder_switch_debounced.pressed:
                encoder_switch_down_at = time.monotonic()
            if self.macropad.encoder_switch_debounced.released and encoder_switch_down_at:
                held_ms = (time.monotonic() - encoder_switch_down_at) * 1000
                self.handle_encoder_switch(held_ms)
                encoder_switch_down_at = None

            beats = self.clock.due_beats()
            for _ in range(beats):
                self.chords.on_beat()

            subticks = self.clock.due_subticks()
            for _ in range(subticks):
                self._on_subtick(self.sub_counter)
                self.sub_counter += 1

            midi_ticks = self.clock.due_midi_ticks()
            for _ in range(midi_ticks):
                self.midi.send(TimingClock())

            self.voice.tick()

            now = time.monotonic()
            if now - self._last_render > 0.05:
                self._last_render = now
                self._render()


App().run()
