# Each press toggles a pad on/off (older picokeypad API style).
# The Pico's own LED blinks from a machine.Timer.
import time
from machine import Pin, Timer
import picokeypad as keypad

keypad.init()
keypad.set_brightness(1.0)

led = Pin(25, Pin.OUT)
Timer(period=500, mode=Timer.PERIODIC, callback=lambda t: led.toggle())

lit = 0
last = 0
while True:
    states = keypad.get_button_states()
    pressed_now = states & ~last        # pads that have just gone down
    last = states
    if pressed_now:
        lit ^= pressed_now
        for i in range(16):
            if lit & (1 << i):
                keypad.illuminate(i, 255, 60, 0)
            else:
                keypad.illuminate(i, 0, 0, 0)
        keypad.update()
    time.sleep_ms(10)                   # MicroPython-only, works here too
