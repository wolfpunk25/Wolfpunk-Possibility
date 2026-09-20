# Wolfpunk Possibility

A small, simple generative melody sequencer for the
[Adafruit MacroPad RP2040](https://www.adafruit.com/product/5128), loosely
modelled on the [OXI One MKII](https://oxiinstruments.com/oxi-one): a
4-chord loop sets the harmony, and a stochastic melody follows it while
continuously drifting - always evolving, rather than looping a fixed
pattern. See [docs/oxi-one-notes.md](docs/oxi-one-notes.md) for the full
mapping from the real instrument's ideas onto this one's keys and pages.

Sister project to [Wolfpunk Foam](https://github.com/wolfpunk25/Wolfpunk-Foam)
(a Herbs and Stones Liquid Foam-inspired groovebox for the same hardware) -
they share the `synthio` voice engine but are otherwise different
instruments with different musical ideas. This repo is self-contained; you
don't need the other one.

## What you get

- A 4-chord diatonic progression (default I-V-vi-IV) you can jump around
  live or edit on the fly, that the melody always follows.
- A stochastic melody generator with real melodic shape, not just
  scale-correct randomness: notes move mostly by step with occasional
  leaps (`ACCUM`) rather than independently each hit, chord tones vs. the
  wider scale is a probability (`WILDNESS`), and downbeats land harder,
  longer and more anchored to the chord than off-beats do.
- Cadential pull - the melody leans toward the *next* chord's tones as the
  current one nears its end, so changes feel anticipated - and phrase
  breathing, where the loop's final bar thins out and relaxes every couple
  of laps before the turnaround, rather than running at constant density
  forever. See [docs/oxi-one-notes.md](docs/oxi-one-notes.md#making-it-actually-musical)
  for the music-theory reasoning behind both.
- A Euclidean rhythm gate (`DENSITY`) instead of a fixed step pattern -
  evenly-spaced hits, adjustable count and grid length.
- `FREEZE` to catch whatever's currently playing and loop it exactly;
  `REROLL` to throw it away for something new; `MUTE` to silence it without
  resetting its internal state - both FREEZE and REROLL confirm with an
  LED flash and on-screen text.
- The same oscillator/filter/envelope/drive voice as Wolfpunk Foam,
  playing live through the onboard speaker in parallel with USB MIDI out,
  now with per-note velocity and length that vary with metric position
  instead of every note sounding identical.
- A live chord/page/parameter readout on the OLED and chord-coloured key
  LEDs.

## Controls

```
 [CHORD1][CHORD2][CHORD3]
 [CHORD4][ OCT- ][ OCT+ ]
 [FREEZE][REROLL][ MUTE ]
 [ PLAY ][ TAP  ][ PAGE ]

        (ENCODER)
```

Full control reference, and what every page's shift-value does, is in
[docs/oxi-one-notes.md](docs/oxi-one-notes.md).

## Installing it

This targets the same Adafruit MacroPad RP2040 as
[Wolfpunk Foam](https://github.com/wolfpunk25/Wolfpunk-Foam) - see that
repo's README for the background on why CIRCUITPY might not be mounting
and how to get into it for the first time. Once the drive is mounted:

```bash
circup --path /Volumes/CIRCUITPY install adafruit_macropad adafruit_debouncer \
    adafruit_simple_text_display neopixel adafruit_display_text adafruit_hid \
    adafruit_midi adafruit_ticks
./tools/install.sh /Volumes/CIRCUITPY
```

`tools/install.sh` copies `CIRCUITPY/` onto the board (rsync + an
AppleDouble sweep - macOS scatters `._*` files across a FAT volume that
CircuitPython then chokes trying to import). It **replaces** whatever
firmware is currently on the board; back that up first if you want it back.

## Repo layout

```
CIRCUITPY/            everything that goes on the board
  code.py              main loop
  boot.py              deliberately empty - keeps the USB drive mounted
  wolfpunk/
    voice.py            oscillator + filter + envelope (ported from Wolfpunk Foam)
    chords.py            the 4-slot diatonic chord loop
    generator.py          the stochastic melody engine: melodic walk, cadential pull, freeze/reroll
    euclid.py             Euclidean rhythm generator
    clock.py              tempo, beat/subtick scheduling, MIDI clock
    scales.py             7 seven-note scales + diatonic triad construction
    ui.py                  OLED + NeoPixel rendering
docs/
  oxi-one-notes.md     what the real instrument does, and the mapping
tools/
  install.sh            copies CIRCUITPY/ onto the mounted board, safely
```

## Changing things

- MIDI channel: `MIDI_CHANNEL` at the top of `code.py`.
- Base note velocity: `VELOCITY` in the same place (actual velocity sent
  varies from this per the metric accent - see `App._metric_weights()`).
- How many laps per phrase before the loop breathes: `PHRASE_LAPS`, also
  at the top of `code.py`.
- Default chord progression: `DEFAULT_SLOTS` in `wolfpunk/chords.py`.
- LED brightness: `macropad.pixels.brightness` in `wolfpunk/ui.py`'s
  `UI.__init__`.
- Add a scale: append a 7-entry semitone list to `SCALES` in
  `wolfpunk/scales.py`.
