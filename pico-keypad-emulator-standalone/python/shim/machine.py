"""
Minimal emulated `machine` module.

Pin 25 / Pin("LED") is the Pico's on-board LED and is shown in the
emulator. I2C and SPI reach emulated versions of the keypad's own chips
(buttons at I2C address 0x20, LEDs on SPI with chip-select on GP17), so
libraries that drive the keypad directly, such as `rgbkeypad`, work.
Timer works, so code that blinks or polls from a timer callback runs as
expected. Other pins are accepted but do nothing.
"""

import threading
import time

import _keypad_bridge as _bridge
import _keypad_hw as _hw

_LED_IDS = (25, "LED", "GP25", "WL_GPIO0")


class Pin:
    IN = 0
    OUT = 1
    OPEN_DRAIN = 2
    ALT = 3
    PULL_UP = 1
    PULL_DOWN = 2
    IRQ_FALLING = 4
    IRQ_RISING = 8

    def __init__(self, id, mode=-1, pull=-1, value=None, **kwargs):
        self._id = id
        self._value = 0
        self._is_led = id in _LED_IDS
        if value is not None:
            self.value(value)

    def init(self, mode=-1, pull=-1, value=None, **kwargs):
        if value is not None:
            self.value(value)

    def value(self, v=None):
        if v is None:
            return self._value
        self._value = 1 if v else 0
        if self._is_led:
            _bridge.set_pico_led(self._value)
        elif _pin_number(self._id) == _hw.PIN_CS:
            _hw.cs_changed(self._value)

    def __call__(self, v=None):
        return self.value(v)

    def on(self):
        self.value(1)

    def off(self):
        self.value(0)

    high = on
    low = off

    def toggle(self):
        self.value(not self._value)

    def irq(self, handler=None, trigger=None, **kwargs):
        return None

    def __repr__(self):
        return "Pin(%r)" % (self._id,)


def _pin_number(p):
    if isinstance(p, Pin):
        p = p._id
    p = getattr(p, "number", p)
    if isinstance(p, str) and p.upper().startswith("GP") and p[2:].isdigit():
        return int(p[2:])
    return p if isinstance(p, int) else None


class I2C:
    """I2C bus. The keypad's button chip answers at address 0x20."""

    def __init__(self, id=0, *, scl=None, sda=None, freq=400000, timeout=50000):
        self._id = id

    def init(self, *args, **kwargs):
        pass

    def deinit(self):
        pass

    def scan(self):
        return _hw.i2c_scan()

    def writeto(self, addr, buf, stop=True):
        return _hw.i2c_write(addr, buf)

    def writevto(self, addr, vector, stop=True):
        data = b"".join(bytes(v) for v in vector)
        _hw.i2c_write(addr, data)
        return len(vector)

    def readfrom(self, addr, nbytes, stop=True):
        return _hw.i2c_read(addr, nbytes)

    def readfrom_into(self, addr, buf, stop=True):
        buf[:] = _hw.i2c_read(addr, len(buf))

    def writeto_mem(self, addr, memaddr, buf, *, addrsize=8):
        _hw.i2c_write(addr, bytes([memaddr]) + bytes(buf))

    def readfrom_mem(self, addr, memaddr, nbytes, *, addrsize=8):
        _hw.i2c_write(addr, bytes([memaddr]))
        return _hw.i2c_read(addr, nbytes)

    def readfrom_mem_into(self, addr, memaddr, buf, *, addrsize=8):
        buf[:] = self.readfrom_mem(addr, memaddr, len(buf))


SoftI2C = I2C


class SPI:
    """SPI bus. Bytes written while GP17 is low drive the keypad's LEDs."""

    MSB = 0
    LSB = 1
    CONTROLLER = MASTER = 0

    def __init__(self, id=0, baudrate=1000000, *, polarity=0, phase=0, bits=8,
                 firstbit=0, sck=None, mosi=None, miso=None):
        self._id = id

    def init(self, *args, **kwargs):
        pass

    def deinit(self):
        pass

    def write(self, buf):
        _hw.spi_write(buf)

    def write_readinto(self, write_buf, read_buf):
        _hw.spi_write(write_buf)
        for i in range(len(read_buf)):
            read_buf[i] = 0

    def read(self, nbytes, write=0):
        return bytes(nbytes)

    def readinto(self, buf, write=0):
        for i in range(len(buf)):
            buf[i] = 0


SoftSPI = SPI


class Timer:
    ONE_SHOT = 0
    PERIODIC = 1

    def __init__(self, id=-1, **kwargs):
        self._stop = None
        if kwargs:
            self.init(**kwargs)

    def init(self, mode=PERIODIC, period=-1, freq=-1, callback=None, tick_hz=1000):
        self.deinit()
        if freq > 0:
            interval = 1.0 / freq
        elif period > 0:
            interval = period / tick_hz
        else:
            raise ValueError("Timer needs a period or freq")
        stop = threading.Event()
        self._stop = stop

        def run():
            nxt = time.perf_counter() + interval
            while not stop.wait(max(0.0, nxt - time.perf_counter())):
                if callback is not None:
                    callback(self)
                if mode == Timer.ONE_SHOT:
                    break
                nxt += interval

        threading.Thread(target=run, name="machine.Timer", daemon=True).start()

    def deinit(self):
        if self._stop is not None:
            self._stop.set()
            self._stop = None


def freq(hz=None):
    return 125000000 if hz is None else None


def reset():
    raise SystemExit("machine.reset() called")


def soft_reset():
    raise SystemExit("machine.soft_reset() called")


def unique_id():
    return b"\xe6\x61\x38\x52\x83\x4c\x2a\x2c"


def idle():
    time.sleep(0.001)


def disable_irq():
    return 0


def enable_irq(state=0):
    pass
