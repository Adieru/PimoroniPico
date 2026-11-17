"""
Link between the emulated Pico (this Python process) and the VS Code
extension that draws the keypad.

Messages are JSON, one per line, over a localhost TCP socket whose port
the extension passes in the PICO_KEYPAD_PORT environment variable.

  Python -> VS Code   {"t": "hello", "token": "..."}
                      {"t": "leds", "d": [[r, g, b] x16], "b": brightness}
                      {"t": "picoled", "v": 0|1}
                      {"t": "exit", "code": 0, "error": "..."}
  VS Code -> Python   {"t": "buttons", "v": <16-bit mask>}

Students never import this module directly.
"""

import json
import os
import socket
import sys
import threading

_sock = None
_send_lock = threading.Lock()
_state_lock = threading.Lock()
_wake = threading.Event()

_buttons = 0
_pending_leds = None      # latest LED frame not yet sent
_last_sent_leds = None
_connected = False


def connected():
    return _connected


def buttons():
    return _buttons


def connect():
    """Connect to the extension. Called once by runner.py before the
    student's program starts."""
    global _sock, _connected
    port = os.environ.get("PICO_KEYPAD_PORT")
    if not port:
        sys.stderr.write(
            "[keypad emulator] Not started from the emulator - running without a "
            "display. Buttons will always read as 0.\n")
        return
    _sock = socket.create_connection(("127.0.0.1", int(port)), timeout=5)
    _sock.settimeout(None)
    _sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    _connected = True
    _send_now({"t": "hello", "token": os.environ.get("PICO_KEYPAD_TOKEN", "")})
    threading.Thread(target=_reader, name="keypad-reader", daemon=True).start()
    threading.Thread(target=_sender, name="keypad-sender", daemon=True).start()


def _send_now(msg):
    if not _connected:
        return
    data = (json.dumps(msg, separators=(",", ":")) + "\n").encode("utf-8")
    with _send_lock:
        try:
            _sock.sendall(data)
        except OSError:
            os._exit(0)  # emulator went away (Stop pressed / panel closed)


def _reader():
    global _buttons
    f = _sock.makefile("r", encoding="utf-8")
    try:
        for line in f:
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if msg.get("t") == "buttons":
                _buttons = int(msg.get("v", 0)) & 0xFFFF
            elif msg.get("t") == "stop":
                break
    except OSError:
        pass
    # Stop pressed, or the keypad panel was closed / a new run started.
    try:
        sys.stdout.write("\n[Stopped by the keypad emulator]\n")
        sys.stdout.flush()
    except Exception:
        pass
    os._exit(0)


def _sender():
    # Coalesces rapid update() calls so a tight animation loop cannot
    # flood the connection: only the newest frame is ever sent.
    while True:
        _wake.wait()
        _wake.clear()
        flush()


def push_leds(frame, brightness):
    """Queue an LED frame (list of 16 [r, g, b]) for display."""
    global _pending_leds
    with _state_lock:
        _pending_leds = (frame, brightness)
    _wake.set()


def flush():
    global _pending_leds, _last_sent_leds
    with _state_lock:
        item = _pending_leds
        _pending_leds = None
    if item is None or item == _last_sent_leds:
        return
    _last_sent_leds = item
    _send_now({"t": "leds", "d": item[0], "b": item[1]})


def set_pico_led(value):
    _send_now({"t": "picoled", "v": 1 if value else 0})


def report_exit(code, error=None):
    flush()
    _send_now({"t": "exit", "code": code, "error": error})


# ------------------------------------------------------------------ attach
# When a program is started by something other than the emulator (Visual
# Studio's F5 / debugger, IDLE, a terminal...), it can still drive an
# emulator window that is already open: the standalone emulator writes its
# address to this file, and the first import of an emulated module connects.

DISCOVERY_FILE = os.path.join(os.path.expanduser("~"), ".pico-keypad-emulator.json")
_reported = False


def report_exit_once(code, error=None):
    global _reported
    if not _reported and _connected:
        _reported = True
        report_exit(code, error)


def _autoconnect():
    if _connected or os.environ.get("PICO_KEYPAD_RUNNER") == "1":
        return
    import _mpcompat
    _mpcompat.install()
    try:
        with open(DISCOVERY_FILE, encoding="utf-8") as f:
            info = json.load(f)
        os.environ["PICO_KEYPAD_PORT"] = str(int(info["bridge_port"]))
        os.environ["PICO_KEYPAD_TOKEN"] = str(info["attach_token"])
        connect()
    except (OSError, ValueError, KeyError):
        sys.stderr.write(
            "[keypad emulator] No emulator window is open - running without a "
            "display. Start the Pico Keypad Emulator first to see the pads.\n")
        return

    import atexit
    previous_hook = sys.excepthook

    def hook(etype, value, tb):
        report_exit_once(1, "%s: %s" % (etype.__name__, value))
        previous_hook(etype, value, tb)

    sys.excepthook = hook
    atexit.register(lambda: report_exit_once(0))


_autoconnect()
