"""
Starts a student's program inside the Pico RGB Keypad emulator.

    python runner.py path/to/main.py

The VS Code extension launches this in a terminal; students do not run
it themselves.
"""

import os
import runpy
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
SHIM = os.path.join(HERE, "shim")


def _student_frames(tb):
    """Traceback frames from the student's code only (hide the emulator)."""
    def is_internal(name):
        return (name.startswith("<frozen") or os.path.basename(name) == "runpy.py"
                or os.path.abspath(name).startswith(HERE + os.sep))
    return [f for f in traceback.extract_tb(tb) if not is_internal(f.filename)]


class _Unavailable:
    """Import hook: these modules don't exist on the chosen firmware."""

    def __init__(self, names, firmware):
        self.names, self.firmware = names, firmware

    def find_spec(self, name, path=None, target=None):
        if name in self.names:
            raise ModuleNotFoundError(
                "No module named '%s'" % name, name=name)
        return None


def _hint(e):
    """A next step for common errors, shown in the keypad panel."""
    if isinstance(e, ModuleNotFoundError) and e.name == "rgbkeypad":
        return ("rgbkeypad.py must be in the same folder as your program. "
                "Run 'Pico Keypad: Add rgbkeypad Library to This Folder' "
                "from the Command Palette.")
    return None


def main():
    if len(sys.argv) < 2:
        print("usage: runner.py <program.py>")
        return 2
    target = os.path.abspath(sys.argv[1])
    os.environ["PICO_KEYPAD_RUNNER"] = "1"   # runner connects; no auto-attach

    # Emulated modules come first so `import picokeypad`, `machine`, etc.
    # always get the emulator, then the student's own folder.
    sys.path.insert(0, os.path.dirname(target))
    sys.path.insert(0, SHIM)
    sys.argv = [target] + sys.argv[2:]

    firmware = os.environ.get("PICO_KEYPAD_FIRMWARE", "micropython").lower()
    if firmware == "circuitpython":
        # CircuitPython has board/busio/digitalio but no machine/picokeypad,
        # so make imports succeed and fail exactly as they would on the Pico.
        sys.path.insert(0, os.path.join(HERE, "shim_cp"))
        sys.meta_path.insert(0, _Unavailable(
            {"machine", "picokeypad", "utime", "urandom"}, "CircuitPython"))
    else:
        import _mpcompat
        _mpcompat.install()
        # Plain desktop Python can't reach these either; just be explicit.
        sys.meta_path.insert(0, _Unavailable(
            {"board", "busio", "digitalio"}, "MicroPython"))
    import _keypad_bridge as bridge
    bridge.connect()

    print("Pico RGB Keypad emulator - running %s  (Ctrl+C or Stop to end)\n"
          % os.path.basename(target), flush=True)

    code, error = 0, None
    try:
        runpy.run_path(target, run_name="__main__")
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        if e.code is not None and not isinstance(e.code, int):
            print(e.code, file=sys.stderr)
    except KeyboardInterrupt:
        print("\nStopped (KeyboardInterrupt)")
        code = 130
    except BaseException as e:  # show the student a clean traceback
        frames = _student_frames(e.__traceback__)
        sys.stderr.write("Traceback (most recent call last):\n")
        sys.stderr.write("".join(traceback.format_list(frames)))
        sys.stderr.write("".join(traceback.format_exception_only(type(e), e)))
        sys.stderr.flush()
        where = ""
        if frames:
            where = " (line %d of %s)" % (frames[-1].lineno,
                                         os.path.basename(frames[-1].filename))
        error = "%s: %s%s" % (type(e).__name__, e, where)
        hint = _hint(e)
        if hint:
            error += "\n\n" + hint
            sys.stderr.write("\n" + hint + "\n")
        code = 1
    else:
        print("\nProgram finished.")

    sys.stdout.flush()
    if bridge.connected():
        bridge.report_exit_once(code, error)
    return code


if __name__ == "__main__":
    sys.exit(main())
