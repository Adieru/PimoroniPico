"""Emulated CircuitPython `digitalio` module.

board.LED (GP25) lights the Pico's LED in the emulator; GP17 is the
chip-select of the keypad's LEDs. Other pins do nothing."""

import _keypad_bridge as _bridge
import _keypad_hw as _hw


class Direction:
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


class Pull:
    UP = "UP"
    DOWN = "DOWN"


class DriveMode:
    PUSH_PULL = "PUSH_PULL"
    OPEN_DRAIN = "OPEN_DRAIN"


class DigitalInOut:
    def __init__(self, pin):
        self._num = getattr(pin, "number", pin)
        self._value = False
        self.direction = Direction.INPUT
        self.pull = None
        self.drive_mode = DriveMode.PUSH_PULL

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = bool(v)
        if self._num == 25:
            _bridge.set_pico_led(self._value)
        elif self._num == _hw.PIN_CS:
            _hw.cs_changed(self._value)

    def switch_to_output(self, value=False, drive_mode=DriveMode.PUSH_PULL):
        self.direction = Direction.OUTPUT
        self.value = value

    def switch_to_input(self, pull=None):
        self.direction = Direction.INPUT
        self.pull = pull

    def deinit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.deinit()
