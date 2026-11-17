# Pico RGB Keypad Emulator: Visual Studio and other editors

This is the standalone version of the keypad emulator, for students who don't use VS Code. It works with Visual Studio (the purple one), IDLE, Thonny, Notepad++, and any other editor.

The keypad opens in your web browser, and your program runs exactly as it would with the VS Code extension. It uses the same `picokeypad` commands, the same errors and the same `rgbkeypad` support.

**You need:** Python 3.8 or newer (from python.org) and a web browser. Nothing else to install.

## 1. Put the emulator somewhere permanent

Unzip `pico-keypad-emulator-standalone.zip` to a folder that won't move, for example `C:\PicoKeypad`. You should see `keypad_emulator.py` and `Start Keypad Emulator.bat` inside.

## 2. Add a "Run on Keypad Emulator" command to Visual Studio (one time)

1. In Visual Studio, open **Tools → External Tools…**
2. Click **Add** and fill in:

   | Field | Value |
   | --- | --- |
   | Title | `Run on Keypad Emulator` |
   | Command | `C:\Windows\py.exe` |
   | Arguments | `-3 "C:\PicoKeypad\keypad_emulator.py" "$(ItemPath)"` |
   | Initial directory | `$(ItemDir)` |
   | Use Output window | ticked |

   If Python was installed without the `py` launcher, set **Command** to the full path of `python.exe` instead. Then use `"C:\PicoKeypad\keypad_emulator.py" "$(ItemPath)"` as the arguments, without the `-3`.
3. Click **OK**. The command now appears in the **Tools** menu.

Optional: to give it a keyboard shortcut, go to **Tools → Options → Environment → Keyboard**. Search for `Tools.ExternalCommand1` (the number matches its position in the External Tools list) and assign keys, e.g. **Ctrl+Alt+K**.

## 3. Use it

1. Open your program (e.g. `main.py`) in Visual Studio.
2. Choose **Tools → Run on Keypad Emulator**. The keypad opens in your browser and the program starts.
3. Edit your code and press **Ctrl+S**. The emulator restarts your program automatically, so there's no need to run the command again.
4. Running the command on a different file sends that file to the same browser tab instead of opening a new one.

Anything your program prints appears in the browser page and in Visual Studio's **Output** window.

To use the keypad in the browser:

- **Press a pad:** click it, or touch it on a touchscreen.
- **Hold several pads at once:** right-click a pad to latch it down, and right-click again to release it.
- **Keyboard:** `1234 / QWER / ASDF / ZXCV`, one row of keys per row of pads.

To stop the emulator, click **Quit** at the bottom of the page.

## 4. Optional: debugging with F5 and breakpoints

Visual Studio can run your program itself, with breakpoints and step-through debugging, while the pads still show in the emulator.

1. Run once, in a terminal, with the same Python that Visual Studio uses:
   ```
   py -3 C:\PicoKeypad\keypad_emulator.py --install
   ```
2. Open the emulator first, using the Tools command above or by double-clicking `Start Keypad Emulator.bat`.
3. In Visual Studio, press **F5** (or **Ctrl+F5**). Your program connects to the open emulator page, and the page shows *Program started by your editor*.

To undo step 1: `py -3 C:\PicoKeypad\keypad_emulator.py --uninstall`.

## Using the rgbkeypad library

Click **Add rgbkeypad library** on the emulator page. It copies `rgbkeypad.py` into your program's folder. Remember to copy that file onto the Pico too when you use the real keypad.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Nothing happens when I choose the Tools command | Check that the Command path exists (`C:\Windows\py.exe`), or use the full path to `python.exe`. |
| The browser didn't open | Look at the Output window: it shows the address, starting `http://127.0.0.1:`. Paste it into your browser. |
| Ctrl+S doesn't restart the program | Check that **Restart when the file is saved** is ticked on the page. |
| F5 runs, but the pads don't change | Open the emulator page before pressing F5, and make sure `--install` was run with the same Python that Visual Studio uses. |
| `ModuleNotFoundError: No module named 'rgbkeypad'` | Click **Add rgbkeypad library** on the page. |
