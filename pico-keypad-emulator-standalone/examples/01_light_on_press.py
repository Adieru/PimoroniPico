# Light each pad while it is held down.
import time
import picokeypad

keypad = picokeypad.PicoKeypad()
keypad.set_brightness(1.0)

NUM_PADS = keypad.get_num_pads()
last_button_states = 0

while True:
    button_states = keypad.get_button_states()
    if button_states != last_button_states:
        last_button_states = button_states
        for i in range(NUM_PADS):
            if button_states & (1 << i):
                keypad.illuminate(i, 0, 255, 80)
            else:
                keypad.illuminate(i, 0, 0, 0)
        keypad.update()
        print("button_states =", button_states)
    time.sleep(0.01)
