"""Emulated CircuitPython `board` module for the Raspberry Pi Pico."""


class Pin:
    def __init__(self, number):
        self.number = number

    def __repr__(self):
        return "board.GP%d" % self.number

    def __eq__(self, other):
        return isinstance(other, Pin) and other.number == self.number

    def __hash__(self):
        return hash(self.number)


for _n in range(29):
    globals()["GP%d" % _n] = Pin(_n)
LED = globals()["GP25"]
del _n
