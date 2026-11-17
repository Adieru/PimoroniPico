"""
Emulation of the two chips on the Pico RGB Keypad Base, for code that
talks to the hardware directly instead of through `picokeypad`
(e.g. Martin O'Hanlon's `rgbkeypad` library, or hand-written drivers).

  * TCA9555 I/O expander at I2C address 0x20 on GP4 (SDA) / GP5 (SCL).
    Its two input-port registers (0 and 1) hold the 16 buttons,
    active-low: a pressed pad reads as 0.
  * 16 APA102 LEDs on SPI0, GP18 (SCK) / GP19 (MOSI), chip-select GP17.
    Each frame is: 4 zero bytes, then per LED [0b111bbbbb, blue, green,
    red], then an end frame.

Bus wrappers in `machine` (MicroPython) and `busio` (CircuitPython) call
into this module.
"""

import errno

import _keypad_bridge as _bridge

I2C_ADDRESS = 0x20
PIN_SDA, PIN_SCL = 4, 5
PIN_CS, PIN_SCK, PIN_MOSI = 17, 18, 19
NUM_LEDS = 16


def _no_device():
    # What MicroPython raises when nothing answers at an I2C address.
    return OSError(errno.ENODEV, "ENODEV")


# ------------------------------------------------------------- TCA9555

class _Tca9555:
    def __init__(self):
        # 0-1 input, 2-3 output, 4-5 polarity inversion, 6-7 configuration
        self.regs = [0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF]
        self.pointer = 0

    def _read_reg(self, r):
        if r in (0, 1):
            raw = (~_bridge.buttons()) & 0xFFFF            # active low
            byte = (raw >> (8 * r)) & 0xFF
            return byte ^ self.regs[4 + r]                   # polarity inversion
        return self.regs[r]

    def write(self, data):
        data = bytes(data)
        if not data:
            return
        self.pointer = data[0] & 0x07
        for b in data[1:]:
            if self.pointer >= 2:                            # inputs are read-only
                self.regs[self.pointer] = b & 0xFF
            self.pointer = (self.pointer & 0x06) | ((self.pointer + 1) & 0x01)

    def read(self, n):
        out = bytearray()
        for _ in range(n):
            out.append(self._read_reg(self.pointer))
            # The TCA9555 toggles between the two registers of a pair.
            self.pointer = (self.pointer & 0x06) | ((self.pointer + 1) & 0x01)
        return bytes(out)


tca = _Tca9555()


def i2c_scan():
    return [I2C_ADDRESS]


def i2c_write(addr, data):
    if addr != I2C_ADDRESS:
        raise _no_device()
    tca.write(data)
    return len(bytes(data))


def i2c_read(addr, n):
    if addr != I2C_ADDRESS:
        raise _no_device()
    return tca.read(n)


# ------------------------------------------------------------- APA102

_spi_buf = bytearray()


def cs_changed(value):
    """Chip-select (GP17) moved: start a fresh LED frame."""
    _spi_buf.clear()


def spi_write(data):
    _spi_buf.extend(bytes(data))
    _try_decode()


def _try_decode():
    buf = _spi_buf
    start = buf.find(b"\x00\x00\x00\x00")
    if start < 0:
        if len(buf) > 4096:
            buf.clear()
        return
    # Skip any extra zero bytes so a long start frame still lines up.
    pos = start + 4
    while pos < len(buf) and buf[pos] == 0:
        pos += 1
    end = pos + 4 * NUM_LEDS
    if len(buf) < end:
        return
    leds, levels = [], []
    for i in range(NUM_LEDS):
        b0, blue, green, red = buf[pos + 4 * i: pos + 4 * i + 4]
        if b0 & 0xE0 != 0xE0:            # not a valid LED frame: give up
            buf.clear()
            return
        leds.append([red, green, blue])
        levels.append((b0 & 0x1F) / 31.0)
    del buf[:end]
    if len(set(levels)) == 1:
        _bridge.push_leds(leds, round(levels[0], 3))
    else:
        # Per-LED brightness: fold it into the colours.
        _bridge.push_leds([[round(c * lv) for c in px] for px, lv in zip(leds, levels)], 1.0)
