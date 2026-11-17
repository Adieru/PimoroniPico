"""
Emulated version of Pimoroni's `picokeypad` MicroPython module for the
Pico RGB Keypad Base.

It supports both styles found in Pimoroni's examples:

    import picokeypad
    keypad = picokeypad.PicoKeypad()      # current style
    keypad.illuminate(0, 255, 0, 0)
    keypad.update()

    import picokeypad as keypad           # older style
    keypad.init()
    keypad.illuminate(0, 255, 0, 0)
    keypad.update()

As on the real device, illuminate() and clear() only change a buffer:
nothing appears on the pads until update() is called.

Pads are numbered 0-15, left to right, top to bottom (0 is top-left
with the Pico's USB socket at the top). get_button_states() returns a
16-bit number where bit n is 1 while pad n is held down.
"""

import _keypad_bridge as _bridge

NUM_PADS = 16
WIDTH = 4
HEIGHT = 4
DEFAULT_BRIGHTNESS = 0.5

_buffer = [[0, 0, 0] for _ in range(NUM_PADS)]
_brightness = DEFAULT_BRIGHTNESS


def _check_int(name, value):
    # MicroPython refuses floats where an int is needed, so the emulator
    # does too - otherwise code would work here and fail on the device.
    if isinstance(value, bool) or not isinstance(value, int):
        if isinstance(value, float):
            raise TypeError("can't convert float to int (%s=%r)" % (name, value))
        raise TypeError("can't convert %s to int (%s=%r)"
                        % (type(value).__name__, name, value))


def init():
    """Set up the keypad (older API). Turns every pad off."""
    global _brightness
    for px in _buffer:
        px[0] = px[1] = px[2] = 0
    _brightness = DEFAULT_BRIGHTNESS
    update()


def get_num_pads():
    """Number of pads on the keypad (always 16)."""
    return NUM_PADS


def get_width():
    return WIDTH


def get_height():
    return HEIGHT


def set_brightness(brightness):
    """Set the brightness of all pads, 0.0 (off) to 1.0 (full).
    Takes effect at the next update()."""
    global _brightness
    if isinstance(brightness, bool) or not isinstance(brightness, (int, float)):
        raise TypeError("can't convert %s to float" % type(brightness).__name__)
    if brightness < 0.0 or brightness > 1.0:
        raise ValueError("brightness out of range. Expected 0.0 to 1.0")
    _brightness = float(brightness)


def illuminate(i, r, g, b):
    """Set pad i (0-15) to colour (r, g, b), each 0-255.
    Takes effect at the next update()."""
    for name, v in (("i", i), ("r", r), ("g", g), ("b", b)):
        _check_int(name, v)
    if i < 0 or i >= NUM_PADS:
        raise ValueError("index out of range. Expected 0 to 15")
    if r < 0 or r > 255:
        raise ValueError("r out of range. Expected 0 to 255")
    if g < 0 or g > 255:
        raise ValueError("g out of range. Expected 0 to 255")
    if b < 0 or b > 255:
        raise ValueError("b out of range. Expected 0 to 255")
    px = _buffer[i]
    px[0], px[1], px[2] = r, g, b


def clear():
    """Turn every pad off. Takes effect at the next update()."""
    for px in _buffer:
        px[0] = px[1] = px[2] = 0


def update():
    """Send the colours set with illuminate()/clear() to the pads."""
    _bridge.push_leds([list(px) for px in _buffer], _brightness)


def get_button_states():
    """Return a 16-bit number: bit n is 1 while pad n is pressed."""
    return _bridge.buttons()


class PicoKeypad:
    """The Pico RGB Keypad Base (current Pimoroni API)."""

    NUM_PADS = NUM_PADS
    WIDTH = WIDTH
    HEIGHT = HEIGHT
    DEFAULT_BRIGHTNESS = DEFAULT_BRIGHTNESS

    def __init__(self):
        init()

    def get_num_pads(self):
        return get_num_pads()

    def set_brightness(self, brightness):
        set_brightness(brightness)

    def illuminate(self, i, r, g, b):
        illuminate(i, r, g, b)

    def clear(self):
        clear()

    def update(self):
        update()

    def get_button_states(self):
        return get_button_states()
