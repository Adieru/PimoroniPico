"""Emulated CircuitPython `busio` module: I2C reaches the keypad's button
chip (address 0x20) and SPI drives its LEDs."""

import _keypad_hw as _hw


class _Lockable:
    _locked = False

    def try_lock(self):
        if self._locked:
            return False
        self._locked = True
        return True

    def unlock(self):
        self._locked = False

    def deinit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.deinit()


def _slice(buf, start, end):
    return bytes(buf)[start:len(buf) if end is None else end]


class I2C(_Lockable):
    def __init__(self, scl, sda, *, frequency=100000, timeout=255):
        pass

    def scan(self):
        return _hw.i2c_scan()

    def writeto(self, address, buffer, *, start=0, end=None):
        _hw.i2c_write(address, _slice(buffer, start, end))

    def readfrom_into(self, address, buffer, *, start=0, end=None):
        end = len(buffer) if end is None else end
        buffer[start:end] = _hw.i2c_read(address, end - start)

    def writeto_then_readfrom(self, address, buffer_out, buffer_in, *,
                              out_start=0, out_end=None, in_start=0, in_end=None):
        self.writeto(address, buffer_out, start=out_start, end=out_end)
        self.readfrom_into(address, buffer_in, start=in_start, end=in_end)


class SPI(_Lockable):
    def __init__(self, clock, MOSI=None, MISO=None, half_duplex=False):
        self.frequency = 250000

    def configure(self, *, baudrate=100000, polarity=0, phase=0, bits=8):
        self.frequency = baudrate

    def write(self, buffer, *, start=0, end=None):
        _hw.spi_write(_slice(buffer, start, end))

    def readinto(self, buffer, *, start=0, end=None, write_value=0):
        end = len(buffer) if end is None else end
        for i in range(start, end):
            buffer[i] = 0

    def write_readinto(self, buffer_out, buffer_in, *, out_start=0, out_end=None,
                       in_start=0, in_end=None):
        self.write(buffer_out, start=out_start, end=out_end)
        self.readinto(buffer_in, start=in_start, end=in_end)
