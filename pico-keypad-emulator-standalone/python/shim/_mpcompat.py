"""
Adds the MicroPython-only parts of `time` and `gc` to desktop Python so
that code written for the Pico runs unchanged in the emulator.
"""

import gc
import time

_TICKS_PERIOD = 1 << 30
_TICKS_MAX = _TICKS_PERIOD - 1
_TICKS_HALF = _TICKS_PERIOD // 2
_start = time.perf_counter()


def _elapsed():
    return time.perf_counter() - _start


def ticks_ms():
    return int(_elapsed() * 1000) & _TICKS_MAX


def ticks_us():
    return int(_elapsed() * 1000000) & _TICKS_MAX


def ticks_cpu():
    return ticks_us()


def ticks_add(ticks, delta):
    return (ticks + delta) & _TICKS_MAX


def ticks_diff(ticks1, ticks2):
    return ((ticks1 - ticks2 + _TICKS_HALF) & _TICKS_MAX) - _TICKS_HALF


def sleep_ms(ms):
    if ms > 0:
        time.sleep(ms / 1000)


def sleep_us(us):
    if us > 0:
        time.sleep(us / 1000000)


def install():
    for name, fn in (("ticks_ms", ticks_ms), ("ticks_us", ticks_us),
                     ("ticks_cpu", ticks_cpu), ("ticks_add", ticks_add),
                     ("ticks_diff", ticks_diff), ("sleep_ms", sleep_ms),
                     ("sleep_us", sleep_us)):
        if not hasattr(time, name):
            setattr(time, name, fn)
    if not hasattr(gc, "mem_free"):
        gc.mem_free = lambda: 192 * 1024   # roughly a fresh Pico
    if not hasattr(gc, "mem_alloc"):
        gc.mem_alloc = lambda: 8 * 1024
    if not hasattr(gc, "threshold"):
        gc.threshold = lambda *a: -1
