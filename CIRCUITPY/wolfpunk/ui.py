# OLED (128x64 SH1106) and NeoPixel rendering. code.py works out what
# everything should say/show; this just draws it.

import displayio
import terminalio
from adafruit_display_text import label

WIDTH = 128
BOX = 22
GAP = 6
BOX_Y = 30
BOX_X0 = 4

# key layout on the 3x4 grid (row-major, keys 0-11)
KEY_CHORDS = (0, 1, 2, 3)
KEY_OCT_DOWN = 4
KEY_OCT_UP = 5
KEY_FREEZE = 6
KEY_REROLL = 7
KEY_MUTE = 8
KEY_PLAY = 9
KEY_TAP = 10
KEY_PAGE = 11

_DEGREE_HUE_STEP = 255 // 7
ROMAN = ["I", "ii", "iii", "IV", "V", "vi", "vii"]


def _wheel(pos):
    pos = pos % 255
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def _scale_rgb(rgb, factor):
    return tuple(int(c * factor) for c in rgb)


class UI:
    def __init__(self, macropad):
        self.macropad = macropad
        macropad.pixels.brightness = 0.2

        self.group = displayio.Group()
        self.line1 = label.Label(terminalio.FONT, text="", color=0xFFFFFF, x=2, y=6)
        self.line2 = label.Label(terminalio.FONT, text="", color=0xFFFFFF, x=2, y=18)
        self.line3 = label.Label(terminalio.FONT, text="", color=0xFFFFFF, x=2, y=58)
        for l in (self.line1, self.line2, self.line3):
            self.group.append(l)

        self.box_bitmap = displayio.Bitmap(WIDTH, BOX, 2)
        self.box_palette = displayio.Palette(2)
        self.box_palette[0] = 0x000000
        self.box_palette[1] = 0xFFFFFF
        self.box_tile = displayio.TileGrid(
            self.box_bitmap, pixel_shader=self.box_palette, x=0, y=BOX_Y
        )
        self.group.append(self.box_tile)

        self.box_labels = []
        for i in range(4):
            x0 = BOX_X0 + i * (BOX + GAP)
            lbl = label.Label(
                terminalio.FONT, text="", color=0x000000, x=x0 + 6, y=BOX_Y + BOX // 2
            )
            self.box_labels.append(lbl)
            self.group.append(lbl)

        macropad.display.root_group = self.group

    def _draw_box(self, i, active):
        x0 = BOX_X0 + i * (BOX + GAP)
        bmp = self.box_bitmap
        for y in range(BOX):
            for x in range(BOX):
                border = x == 0 or y == 0 or x == BOX - 1 or y == BOX - 1
                bmp[x0 + x, y] = 1 if (active or border) else 0
        self.box_labels[i].color = 0x000000 if active else 0xFFFFFF

    def render(self, page_line, status_line, info_line, chord_slots, active_slot):
        self.line1.text = page_line[:21]
        self.line2.text = status_line[:21]
        self.line3.text = info_line[:21]
        for i in range(4):
            self._draw_box(i, i == active_slot)
            self.box_labels[i].text = ROMAN[chord_slots[i]]

    def leds(self, chord_slots, active_slot, running, frozen, muted, shift_held):
        px = self.macropad.pixels
        for i in KEY_CHORDS:
            hue = chord_slots[i] * _DEGREE_HUE_STEP
            base = _wheel(hue)
            px[i] = base if i == active_slot else _scale_rgb(base, 0.3)

        px[KEY_OCT_DOWN] = (0, 40, 90)
        px[KEY_OCT_UP] = (90, 45, 0)
        px[KEY_FREEZE] = (0, 130, 130) if frozen else (0, 25, 25)
        px[KEY_REROLL] = (70, 70, 70)
        px[KEY_MUTE] = (110, 0, 0) if muted else (20, 0, 0)
        px[KEY_PLAY] = (0, 90, 0) if running else (90, 0, 0)
        px[KEY_TAP] = (70, 60, 0)
        px[KEY_PAGE] = (255, 255, 255) if shift_held else (60, 60, 60)
        px.show()
