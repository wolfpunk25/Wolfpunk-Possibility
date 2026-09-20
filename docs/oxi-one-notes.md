# OXI One MKII, simplified - and how it maps to Wolfpunk Possibility

The [OXI One MKII](https://oxiinstruments.com/oxi-one) is a performance
sequencer built around eight independent sequencers (mono, poly, chord,
matricial, stochastic, multitrack) that can run together, each generating
notes, chords, rhythm or modulation its own way. A chord sequencer often
acts as a harmonic anchor for the others, so a piece can stay coherent even
while several parts are semi-randomly generating their own material.

Wolfpunk Possibility takes one slice of that idea - a chord reference plus
a stochastic melody that follows it - and builds it as a single, always-on
generative voice, since a 12-key, one-encoder controller has nowhere near
the surface for eight parallel sequencers and six sequencing modes.
Patching/routing, CV/gate I/O, projects and pattern slots are all left out
entirely; this is one instrument doing one thing continuously; the reviewer
transcript's most true version.

## What's kept, and what it became

| OXI One MKII | Wolfpunk Possibility |
|---|---|
| Chord sequencer as harmonic reference | The 4 `CHORD` keys: a 4-slot diatonic chord loop (default I-V-vi-IV). Tap to jump live; hold + turn the encoder to change that slot's chord. |
| Stochastic mode (note pool + probabilities) | The generative engine in [`generator.py`](../CIRCUITPY/wolfpunk/generator.py): each hit picks a chord tone or a wider scale tone, weighted by `WILDNESS`. |
| Accumulator (pitch drifts over repetitions) | `ACCUM` page: a slow random-walk drift added to each note's octave, instead of every note being independently random - see `Generator._accum`. |
| Euclidean rhythm generator | `DENSITY` page: an evenly-spaced Euclidean gate (hits out of steps) decides which subdivisions actually get a note. |
| "A pattern can be completely fixed if you want it to repeat exactly" | `FREEZE`: stops drawing new randomness and replays the last full lap - both its rhythm and pitches - exactly. |
| Muting a pattern vs. muting a whole sequencer | `MUTE`: silences the output but keeps the generator's internal state (accumulator, buffer) evolving underneath, so unmuting resumes mid-thought rather than restarting cold. |
| Randomiser / regenerate | `REROLL`: reseeds the generator and clears its buffer for a fresh take. Also on the encoder's short click. |
| Scale quantisation, per-sequencer root/scale | `SCALE` page: 7 seven-note scales, with root note on the encoder's shift value. Every generated note is scale-quantised by construction, not as a filter. |
| Global BPM, tap tempo | `TAP` key, and `TEMPO` page (BPM + subdivision, i.e. how many grid steps per beat). |
| CV/gate outputs to Eurorack | Not present - MIDI out only (see below), same simplification made in the sister project. |
| Two LFOs per sequencer, CV modulation | Not carried over in this version - kept the control surface to one clear idea (chord + stochastic melody) rather than stacking on filter/CV modulation too. |

## The instrument, in one paragraph

A chord loop of 4 slots advances every `beats_per_chord` beats (`ACCUM`
page, shift value). On every Euclidean-gated subdivision, the generator
either stays on the current chord's root/third/fifth or reaches for a wider
scale tone (`WILDNESS`), and nudges a slow pitch drift up or down an octave
or so (`ACCUM`). The result plays live through the onboard speaker via the
same `synthio` voice engine as [Wolfpunk Foam](https://github.com/wolfpunk25/Wolfpunk-Foam)
(oscillator blend, resonant filter, decay envelope, drive), and out over USB
MIDI at the same time. `FREEZE` catches whatever's currently playing and
loops it exactly; `REROLL` throws it away for something new; `MUTE` lets it
keep thinking without being heard; the 4 `CHORD` keys let you conduct the
harmony live while all of that keeps running underneath.

## Controls

```
 [CHORD1][CHORD2][CHORD3]
 [CHORD4][ OCT- ][ OCT+ ]
 [FREEZE][REROLL][ MUTE ]
 [ PLAY ][ TAP  ][ PAGE ]

        (ENCODER)
```

- **CHORD 1-4** - tap to jump the progression to that slot immediately (it
  then holds for `beats_per_chord` beats before auto-advancing again, same
  as normal). Hold + turn the encoder to change that slot's chord (a
  diatonic triad built on a scale degree, shown as a roman numeral).
- **OCT- / OCT+** - shift the whole melody up or down an octave, live.
- **FREEZE** - toggle: stop generating new material and loop the last full
  bar exactly, both its rhythm and its pitches.
- **REROLL** - throw away the current generative state and start fresh from
  a new random seed. Also un-freezes if it was frozen.
- **MUTE** - toggle: silence the output (speaker + MIDI) without stopping
  the generator's own internal evolution.
- **PLAY** - start/stop the internal clock (also sends MIDI Start/Stop).
- **TAP** - tap tempo. Two taps within 2 seconds sets the BPM.
- **PAGE** - tap to cycle the encoder's page (`WILDNESS`, `DENSITY`,
  `ACCUM`, `WAVE`, `FILTER`, `ENV`, `DRIVE`, `TEMPO`, `SCALE`). Hold it down
  and turn the encoder to edit that page's *second* parameter instead.
- **Encoder** - turn to edit the current page's value. Short click:
  REROLL. Long-press (>0.6s): toggle FREEZE - same actions as the dedicated
  keys, for quick access without moving your hand.

## Installing it

Same hardware and installation path as
[Wolfpunk Foam](https://github.com/wolfpunk25/Wolfpunk-Foam) - see that
repo's README for the CIRCUITPY-drive/REPL background if you haven't been
through it before. In short:

```bash
circup --path /Volumes/CIRCUITPY install adafruit_macropad adafruit_debouncer \
    adafruit_simple_text_display neopixel adafruit_display_text adafruit_hid \
    adafruit_midi adafruit_ticks
./tools/install.sh /Volumes/CIRCUITPY
```

If you're flashing this onto the same MacroPad that was running Wolfpunk
Foam, back that up first (`tools/install.sh` doesn't do this for you) - it
will fully replace it.
