from rgbkeypad import RGBKeypad
import time

keypad = RGBKeypad()

keypad.color = (0,0,0)

WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
CLEAR = (0, 0, 0)

colours = [RED, GREEN, BLUE, YELLOW, PURPLE, WHITE]

colour_index = 0

# turn a key blue when pressed
while True:
    for key in keypad.keys:
        if key.is_pressed():

            colour_index = (colour_index + 1) % 5
            next_colour = colours[(colour_index + 1) % 7]
            key.color = next_colour

            for i in range(0, 4):
                if key.x + i < 4:
                    light_key = keypad[(key.x + i), key.y]
                    light_key.color = next_colour

                if key.x - i > -1:
                    light_key = keypad[(key.x - i), key.y]
                    light_key.color = next_colour

                if key.y + i < 4:
                    light_key = keypad[key.x, (key.y+i)]
                    light_key.color = next_colour

                if key.y + i > -1:
                    light_key = keypad[key.x, (key.y-i)]
                    light_key.color = next_colour

                time.sleep(0.1)

            for i in range(0, 4):
                if key.x + i < 4:
                    light_key = keypad[(key.x + i), key.y]
                    light_key.color = CLEAR

                if key.x - i > -1:
                    light_key = keypad[(key.x - i), key.y]
                    light_key.color = CLEAR

                if key.y + i < 4:
                    light_key = keypad[key.x, (key.y+i)]
                    light_key.color = CLEAR

                if key.y + i > -1:
                    light_key = keypad[key.x, (key.y-i)]
                    light_key.color = CLEAR

                time.sleep(0.1)

            print(light_key.x, light_key.y)

    time.sleep(0.1)
