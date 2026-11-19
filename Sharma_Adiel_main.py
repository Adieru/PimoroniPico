from token import STAR
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

#Keys index
PadKeys = []
for i in range(4):
    for j in range(4):

        PadKeys.append(keypad[i, j])

#If a key is pressed
def CheckClick():
    for key in PadKeys:
        if(key.is_pressed()):
            return True

    return False

#Finds which key is pressed:
def GetPressedKey():
    keyIndex = 00

    for key in PadKeys:
        if(key.is_pressed()):
            keyIndex = key

            return keyIndex
    return
   
#Start function
def StartGame(): #Note only use it with the CheckClick function
    if(PadKeys[5].is_pressed() or PadKeys[6].is_pressed() or PadKeys[9].is_pressed() or PadKeys[10].is_pressed()):
        return True

    return False

#Checks if the player has clicked in the correct slot
InRange = []
for i in range(1, 5):
    for j in range(1, 5):
        if(i != 4 and j != 4):
            InRange.append(keypad[i - 1, j - 1])

#Checks if pressed key is within the range
def CheckRange(StartStatus, ClickStatus):

    if(StartStatus and ClickStatus):
        if(PadKeys[GetPressedKey()] in InRange):
            return True

    return False   

#Set the colours to 'X'
def SetX(ColorOne, ColorTwo):
    #The 'X'
    keypad[0, 0].color = ColorOne
    keypad[1, 1].color = ColorOne
    keypad[2, 2].color = ColorOne
    keypad[3, 3].color = ColorOne

    keypad[0, 3].color = ColorOne
    keypad[1, 2].color = ColorOne
    keypad[2, 1].color = ColorOne
    keypad[3, 0].color = ColorOne

    #The background
    keypad[0, 1].color = ColorTwo
    keypad[0, 2].color = ColorTwo
    keypad[3, 1].color = ColorTwo
    keypad[3, 2].color = ColorTwo

    keypad[1, 0].color = ColorTwo   
    keypad[2, 0].color = ColorTwo
    keypad[1, 3].color = ColorTwo
    keypad[2, 3].color = ColorTwo

#Clears the board:
def ClearBoard():
    for i in range(4):
        for j in range(4):

            keypad[i, j].color = CLEAR

def Main():
    GameLoop = True
    #The main loop for the game
    while GameLoop:

        #Starts the game:
        if(StartGame()):

            time.sleep(0.2)
            SetX(PURPLE, GREEN)

            time.sleep(1)
            ClearBoard()






Main()

