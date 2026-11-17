# A rainbow that scrolls across the keypad. Press any pad to freeze it.
import time
import picokeypad

keypad = picokeypad.PicoKeypad()
keypad.set_brightness(0.5)


def wheel(pos):
    """Colour wheel: 0-255 in, (r, g, b) out."""
    pos = pos % 256
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


offset = 0
while True:
    if keypad.get_button_states() == 0:
        offset += 4
    for i in range(16):
        x, y = i % 4, i // 4
        r, g, b = wheel(offset + (x + y) * 24)
        keypad.illuminate(i, r, g, b)
    keypad.update()
    time.sleep(0.03)
