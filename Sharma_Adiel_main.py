from ast import Break
from token import STAR
from tracemalloc import start
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

    Clicked = 0

    for i in range(len(PadKeys) - 1):
        if(PadKeys[i].is_pressed()):
            Clicked = i

            return Clicked

    return 

#Finds which key is pressed:
'''
def GetPressedKey():
    keyIndex = 00

    for key in PadKeys:
        if(key.is_pressed()):
            keyIndex = key

            return keyIndex
    return
'''
   
#Start function
def StartGame(): #Note only use it with the CheckClick function
    if(PadKeys[5].is_pressed() or PadKeys[6].is_pressed() or PadKeys[9].is_pressed() or PadKeys[10].is_pressed()):
        return True

    return False

#Checks if the player has clicked in the correct slot
Range = []
for i in range(1, 13):
    if(i % 4 != 0):
        Range.append(i - 1)

#Checks if pressed key is within the range
def CheckRange():
    Clicked_Key = CheckClick()

    if(Clicked_Key in Range):
       #print("In Range")
       return True

    #print("Not Range")

    return False   

#Set the board to 'X'
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
    keypad.color = CLEAR

#Set Color, for press
def SetColor(IsPlayerOne):
    if(IsPlayerOne):
        IsPlayerOne = False




    else:
        IsPlayerOne = True

def Main():
    GameLoop = True
    Start = False
    PlayerOneStatus = False

    #The main loop for the game
    while True:

        
        for i in range(0,16):

                if(PadKeys[i].is_pressed()):
                    if(Start == True and CheckRangeRan == True) : CheckRangeRan = False

                    if(Start != True and StartGame()):
                        CheckRangeRan = False
                        Start = True
                        PlayerOneStatus = True
                        SetX(PURPLE, GREEN)
                        time.sleep(1)
                        ClearBoard()

                    elif(CheckRangeRan == False and CheckRange() != True):
                        CheckRangeRan = True
                        Start = False
                        SetX(YELLOW, RED)
                        time.sleep(3)
                        ClearBoard()


                    elif(CheckRangeRan == False and CheckRange()):
                        CheckRangeRan = True

                        #Game Logic here
                        SetColor(PlayerOneStatus)

                               

Main()

