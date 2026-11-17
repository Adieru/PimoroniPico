@echo off
rem Starts the Pico RGB Keypad Emulator. Drag a .py file onto this to run it.
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0keypad_emulator.py" %*
) else (
    python "%~dp0keypad_emulator.py" %*
)
if errorlevel 1 pause
