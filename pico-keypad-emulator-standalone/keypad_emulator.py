#!/usr/bin/env python3
"""
Pico RGB Keypad Emulator - standalone version (no VS Code needed).

Opens the clickable 4x4 keypad in your web browser and runs a MicroPython
program for the Pimoroni Pico RGB Keypad Base with desktop Python. Works
with any editor: Visual Studio, IDLE, Thonny, Notepad++...

    python keypad_emulator.py                 open the emulator
    python keypad_emulator.py main.py         open it and run main.py
    python keypad_emulator.py --install       let programs started by your
                                              editor (e.g. Visual Studio F5)
                                              find `picokeypad` and connect
    python keypad_emulator.py --uninstall     undo --install

If an emulator is already open, running this again with a file sends the
file to that window instead of opening a second one.

Needs only Python 3.8+ (standard library).
"""

import argparse
import json
import os
import queue
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PY_DIR = os.path.join(HERE, "python")
SHIM = os.path.join(PY_DIR, "shim")
RUNNER = os.path.join(PY_DIR, "runner.py")
MEDIA = os.path.join(HERE, "media")
DISCOVERY_FILE = os.path.join(os.path.expanduser("~"), ".pico-keypad-emulator.json")
PTH_NAME = "pico_keypad_emulator.pth"
NUM_PADS = 16


# ======================================================================
# Emulator state: the program process, the bridge socket, the browser pages
# ======================================================================

class Emulator:
    def __init__(self):
        self.lock = threading.RLock()
        self.clients = []                       # one queue per open browser tab
        self.file = None
        self.auto_restart = True
        self.firmware = "micropython"
        self.status = "idle"
        self.error = None
        self.attached = False
        self.buttons = 0
        self.proc = None
        self.conn = None
        self.run_token = None
        self.attach_token = secrets.token_hex(12)
        self.mtime = None
        self.reset_device()

    def reset_device(self):
        self.leds = [[0, 0, 0] for _ in range(NUM_PADS)]
        self.brightness = 0.5
        self.pico_led = 0

    # ------------------------------------------------------------ pages

    def subscribe(self):
        q = queue.Queue()
        with self.lock:
            self.clients.append(q)
        return q

    def unsubscribe(self, q):
        with self.lock:
            if q in self.clients:
                self.clients.remove(q)

    def broadcast(self, msg):
        with self.lock:
            for q in list(self.clients):
                q.put(msg)

    def state_msg(self):
        fw = "CircuitPython" if self.firmware == "circuitpython" else "MicroPython"
        if self.attached:
            label = "Program started by your editor  \u00b7  " + fw
        elif self.file:
            label = os.path.basename(self.file) + "  \u00b7  " + fw
        else:
            label = None
        return {"type": "state", "leds": self.leds, "brightness": self.brightness,
                "picoLed": self.pico_led, "status": self.status, "error": self.error,
                "file": label}

    def config_msg(self):
        return {"type": "config", "file": self.file or "", "autoRestart": self.auto_restart,
                "firmware": self.firmware}

    def post_state(self):
        self.broadcast(self.state_msg())

    def post_leds(self):
        self.broadcast({"type": "leds", "leds": self.leds, "brightness": self.brightness,
                        "picoLed": self.pico_led})

    def out(self, text):
        sys.stdout.write(text)
        sys.stdout.flush()
        self.broadcast({"type": "out", "text": text})

    def set_status(self, status, error=None):
        with self.lock:
            self.status, self.error = status, error
        self.post_state()

    # ------------------------------------------------------------ messages from the page

    def on_page_message(self, msg):
        t = msg.get("type")
        if t == "ready":
            return [self.config_msg(), self.state_msg()]
        if t == "buttons":
            self.buttons = int(msg.get("value", 0)) & 0xFFFF
            self.send({"t": "buttons", "v": self.buttons})
        elif t == "run":
            self.run()
        elif t == "stop":
            self.stop("stopped")
        elif t == "setFile":
            self.set_file(msg.get("file", ""))
        elif t == "setOption":
            if "autoRestart" in msg:
                self.auto_restart = bool(msg["autoRestart"])
            if msg.get("firmware") in ("micropython", "circuitpython"):
                self.firmware = msg["firmware"]
                self.post_state()
            self.broadcast(self.config_msg())
        elif t == "addLibrary":
            return [self.add_library()]
        elif t == "quit":
            threading.Thread(target=shutdown, daemon=True).start()
        return []

    def set_file(self, path):
        path = os.path.abspath(os.path.expanduser(path.strip().strip('"'))) if path.strip() else None
        if path and not os.path.isfile(path):
            self.broadcast({"type": "notice", "text": "File not found: " + path, "error": True})
            return False
        self.file = path
        self.mtime = os.path.getmtime(path) if path else None
        self.broadcast(self.config_msg())
        self.post_state()
        return True

    def add_library(self):
        if not self.file:
            return {"type": "notice", "text": "Choose your program file first.", "error": True}
        dest = os.path.join(os.path.dirname(self.file), "rgbkeypad.py")
        if os.path.exists(dest):
            return {"type": "notice", "text": "rgbkeypad.py is already in " + os.path.dirname(self.file)}
        shutil.copyfile(os.path.join(PY_DIR, "libs", "rgbkeypad.py"), dest)
        return {"type": "notice", "text": "Added rgbkeypad.py next to your program. "
                "Copy it onto the Pico too when you use the real keypad."}

    # ------------------------------------------------------------ run / stop

    def run(self):
        if not self.file:
            self.set_status("error", "No program chosen. Enter the path of your .py file above, "
                                     "or start the emulator from Visual Studio.")
            return
        if not os.path.isfile(self.file):
            self.set_status("error", "File not found: " + self.file)
            return
        self.stop(None)
        with self.lock:
            self.reset_device()
            self.attached = False
            self.run_token = secrets.token_hex(12)
            self.mtime = os.path.getmtime(self.file)
        self.broadcast({"type": "clear"})
        self.set_status("starting")
        env = dict(os.environ)
        env.update({
            "PICO_KEYPAD_PORT": str(BRIDGE_PORT),
            "PICO_KEYPAD_TOKEN": self.run_token,
            "PICO_KEYPAD_FIRMWARE": self.firmware,
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
        })
        kwargs = {}
        if os.name == "nt":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        proc = subprocess.Popen(
            [sys.executable, RUNNER, self.file], cwd=os.path.dirname(self.file), env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
        self.proc = proc
        threading.Thread(target=self._pump, args=(proc, self.run_token), daemon=True).start()

    def _pump(self, proc, token):
        for raw in iter(proc.stdout.readline, b""):
            self.out(raw.decode("utf-8", "replace"))
        code = proc.wait()
        with self.lock:
            if self.run_token == token and self.status in ("starting", "running"):
                # Exited without reporting (e.g. a crash before connecting).
                if self.status == "starting":
                    self.set_status("error", "The program stopped before it started - see the output below.")
                else:
                    self.set_status("finished" if code == 0 else "stopped")

    def stop(self, new_status):
        with self.lock:
            was_running = self.status in ("starting", "running")
            self.run_token = None
            conn, self.conn = self.conn, None
            proc, self.proc = self.proc, None
        if conn:
            try:
                conn.sendall(b'{"t":"stop"}\n')
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conn.close()
        if proc and proc.poll() is None:
            def reap():
                try:
                    proc.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            threading.Thread(target=reap, daemon=True).start()
        if new_status and was_running:
            self.set_status(new_status)

    # ------------------------------------------------------------ bridge (program side)

    def send(self, msg):
        conn = self.conn
        if conn:
            try:
                conn.sendall((json.dumps(msg) + "\n").encode("utf-8"))
            except OSError:
                pass

    def on_connection(self, conn):
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        f = conn.makefile("r", encoding="utf-8")
        try:
            hello = json.loads(f.readline() or "{}")
        except ValueError:
            conn.close()
            return
        token = hello.get("token")
        with self.lock:
            if token and token == self.run_token:
                self.attached = False
            elif token == self.attach_token:
                # A program started by the editor: it takes over the keypad.
                pass
            else:
                conn.close()
                return
        if token == self.attach_token:
            self.stop(None)
            with self.lock:
                self.reset_device()
                self.attached = True
                self.run_token = None
        with self.lock:
            old, self.conn = self.conn, conn
        if old:
            old.close()
        self.set_status("running")
        self.post_leds()
        self.send({"t": "buttons", "v": self.buttons})
        try:
            for line in f:
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                self.on_program_message(msg)
        except (OSError, ValueError):
            pass
        with self.lock:
            mine = self.conn is conn
            if mine:
                self.conn = None
        if mine and self.status in ("starting", "running"):
            self.set_status("finished")

    def on_program_message(self, msg):
        t = msg.get("t")
        if t == "leds":
            if isinstance(msg.get("d"), list) and len(msg["d"]) == NUM_PADS:
                self.leds = msg["d"]
            if isinstance(msg.get("b"), (int, float)):
                self.brightness = msg["b"]
            self.post_leds()
        elif t == "picoled":
            self.pico_led = 1 if msg.get("v") else 0
            self.post_leds()
        elif t == "exit":
            if msg.get("error"):
                self.set_status("error", msg["error"])
            else:
                self.set_status("stopped" if msg.get("code") == 130 else "finished")

    # ------------------------------------------------------------ restart on save

    def watch(self):
        while True:
            time.sleep(0.5)
            f = self.file
            if not f or not self.auto_restart:
                continue
            try:
                m = os.path.getmtime(f)
            except OSError:
                continue
            if self.mtime is not None and m != self.mtime:
                self.mtime = m
                time.sleep(0.15)   # let the editor finish writing
                self.out("\n[File saved - restarting]\n")
                self.run()
            self.mtime = m


EMU = Emulator()
BRIDGE_PORT = 0
HTTP_PORT = 0
SESSION_KEY = secrets.token_urlsafe(16)
HTTPD = None


# ======================================================================
# Web page
# ======================================================================

def page_html():
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pico RGB Keypad Emulator</title>
<link rel="stylesheet" href="/media/keypad.css">
<style>
:root, body {
  --vscode-font-family: 'Segoe UI', system-ui, -apple-system, Arial, sans-serif;
  --vscode-font-size: 14px;
  --vscode-editor-font-family: Consolas, 'Cascadia Mono', Menlo, monospace;
  --vscode-editor-background: #1e1e1e; --vscode-foreground: #d4d4d4;
  --vscode-button-background: #6f42c1; --vscode-button-foreground: #fff; --vscode-button-hoverBackground: #8257e5;
  --vscode-button-secondaryBackground: #3a3d41; --vscode-button-secondaryForeground: #fff;
  --vscode-button-secondaryHoverBackground: #45494e;
  --vscode-widget-border: #454545; --vscode-focusBorder: #8257e5; --vscode-charts-green: #3fb950;
  --vscode-inputValidation-errorBackground: #5a1d1d; --vscode-inputValidation-errorBorder: #be1100;
  --vscode-inputValidation-errorForeground: #fff;
}
body { padding-top: 16px; }
#app { max-width: 480px; }
h1 { font-size: 16px; font-weight: 600; margin: 0 0 12px; opacity: .9; }
.prog { display: flex; gap: 6px; margin-bottom: 10px; }
.prog input { flex: 1; min-width: 0; font: 13px var(--vscode-editor-font-family); padding: 5px 8px;
  color: #d4d4d4; background: #2d2d2d; border: 1px solid #454545; border-radius: 3px; user-select: text; }
.opts { display: flex; flex-wrap: wrap; gap: 6px 16px; align-items: center; margin: 14px 0 6px; font-size: 13px; }
.opts select { background: #2d2d2d; color: #d4d4d4; border: 1px solid #454545; border-radius: 3px; padding: 2px 4px; }
.notice { margin-top: 8px; font-size: 13px; color: #9cdcfe; min-height: 1em; }
.notice.bad { color: #f48771; }
.console-head { display: flex; justify-content: space-between; align-items: center; margin-top: 14px; font-size: 13px; }
.console-head button { padding: 1px 8px; font-size: 12px; }
#console { margin: 4px 0 0; height: 170px; overflow: auto; background: #111; color: #ccc; border: 1px solid #333;
  border-radius: 4px; padding: 6px 8px; font: 12.5px/1.4 var(--vscode-editor-font-family); white-space: pre-wrap;
  user-select: text; -webkit-user-select: text; }
.foot { margin-top: 14px; font-size: 12px; opacity: .6; display: flex; justify-content: space-between; }
.foot a { color: inherit; cursor: pointer; }
</style></head>
<body>
<div id="app" data-options='{"showPadNumbers": true, "keyboard": true}'>
  <h1>Pico RGB Keypad Emulator</h1>
  <div class="prog">
    <input id="path" placeholder="Path of your program, e.g. C:\\Users\\you\\keypad\\main.py" spellcheck="false">
    <button id="setpath" title="Use this file">Use</button>
  </div>
  <div class="toolbar">
    <button id="run" title="Run your program">&#9654; Run</button>
    <button id="stop" title="Stop the program">&#9632; Stop</button>
    <span id="status" class="status idle">Idle</span>
  </div>
  <div id="file" class="file"></div>
  <div id="error" class="errbox" hidden></div>

  <div class="device">
    <div class="pico">
      <div class="usb"></div>
      <div class="chip">RP2040</div>
      <div id="picoled" class="picoled" title="On-board LED (Pin 25 / Pin('LED'))"></div>
      <div class="pico-label">Raspberry Pi Pico</div>
    </div>
    <div class="base">
      <div id="grid" class="grid" role="grid" aria-label="Keypad"></div>
      <div class="brand">PIMORONI &middot; PICO RGB KEYPAD</div>
    </div>
  </div>

  <div class="readout">
    <code>get_button_states()</code> =
    <span id="mask-bin" class="mono">0b0000000000000000</span>
    <span id="mask-dec" class="mono">(0)</span>
  </div>
  <div class="brightness">brightness: <span id="bright" class="mono">0.50</span></div>

  <div class="opts">
    <label><input type="checkbox" id="auto"> Restart when the file is saved</label>
    <label>Firmware <select id="fw"><option value="micropython">MicroPython</option>
      <option value="circuitpython">CircuitPython</option></select></label>
    <button id="addlib" title="Copy rgbkeypad.py into your program's folder">Add rgbkeypad library</button>
  </div>
  <div id="notice" class="notice"></div>

  <div class="console-head"><span>Program output</span><button id="clear">Clear</button></div>
  <pre id="console"></pre>

  <details class="help">
    <summary>How to use</summary>
    <ul>
      <li><b>Click / touch</b> a pad to hold it down.</li>
      <li><b>Right-click</b> (or Shift+click) a pad to latch it down; right-click again to release.</li>
      <li id="kb-help"><b>Keyboard</b> (click the keypad first): <span class="mono">1 2 3 4</span> / <span class="mono">Q W E R</span> / <span class="mono">A S D F</span> / <span class="mono">Z X C V</span>.</li>
      <li>Pads are numbered 0-15, left to right, top to bottom.</li>
      <li>Leave this tab open while you work. Saving your program restarts it here.</li>
    </ul>
  </details>
  <div class="foot"><span>Close the console window (or click Quit) to stop the emulator.</span><a id="quit">Quit</a></div>
</div>
<script>
(function () {
  const KEY = new URLSearchParams(location.search).get('k') || '';
  const post = (m) => fetch('/api/msg', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Keypad-Key': KEY },
                                          body: JSON.stringify(m) })
    .then(r => r.json()).then(list => list.forEach(x => window.postMessage(x, '*'))).catch(() => {});
  window.acquireVsCodeApi = () => ({ postMessage: post });
  const es = new EventSource('/events?k=' + encodeURIComponent(KEY));
  es.onmessage = (e) => window.postMessage(JSON.parse(e.data), '*');
  es.onopen = () => post({ type: 'ready' });

  const $ = (id) => document.getElementById(id);
  const con = $('console'), notice = $('notice');
  window.addEventListener('message', (e) => {
    const m = e.data;
    if (m.type === 'config') {
      if (document.activeElement !== $('path')) $('path').value = m.file;
      $('auto').checked = m.autoRestart; $('fw').value = m.firmware;
    } else if (m.type === 'out') {
      const atEnd = con.scrollTop + con.clientHeight >= con.scrollHeight - 4;
      con.textContent += m.text;
      if (con.textContent.length > 200000) con.textContent = con.textContent.slice(-150000);
      if (atEnd) con.scrollTop = con.scrollHeight;
    } else if (m.type === 'clear') {
      con.textContent = '';
    } else if (m.type === 'notice') {
      notice.textContent = m.text; notice.className = 'notice' + (m.error ? ' bad' : '');
    }
  });
  $('setpath').onclick = () => post({ type: 'setFile', file: $('path').value });
  $('path').addEventListener('keydown', (e) => { if (e.key === 'Enter') post({ type: 'setFile', file: $('path').value }).then(() => post({ type: 'run' })); });
  $('auto').onchange = () => post({ type: 'setOption', autoRestart: $('auto').checked });
  $('fw').onchange = () => post({ type: 'setOption', firmware: $('fw').value });
  $('addlib').onclick = () => post({ type: 'addLibrary' });
  $('clear').onclick = () => { con.textContent = ''; };
  $('quit').onclick = () => { post({ type: 'quit' }); document.body.innerHTML = '<p style="padding:20px">Emulator closed. You can close this tab.</p>'; };
})();
</script>
<script src="/media/keypad.js"></script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "PicoKeypadEmulator/1.3"

    def log_message(self, *args):
        pass

    def _host_ok(self):
        # Refuse requests not addressed to us by name (blocks DNS rebinding).
        return self.headers.get("Host", "") in ("127.0.0.1:%d" % HTTP_PORT, "localhost:%d" % HTTP_PORT)

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, "{}")
        path, _, query = self.path.partition("?")
        if path == "/":
            return self._send(200, page_html(), "text/html; charset=utf-8")
        if path in ("/media/keypad.css", "/media/keypad.js"):
            with open(os.path.join(MEDIA, os.path.basename(path)), "rb") as f:
                ctype = "text/css" if path.endswith(".css") else "text/javascript"
                return self._send(200, f.read(), ctype + "; charset=utf-8")
        if path == "/api/ping":
            return self._send(200, '{"ok": true}')
        if path == "/events":
            if ("k=" + SESSION_KEY) not in query:
                return self._send(403, "{}")
            return self._events()
        self._send(404, "{}")

    def _events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        q = EMU.subscribe()
        try:
            while True:
                try:
                    msg = q.get(timeout=15)
                    self.wfile.write(("data: " + json.dumps(msg) + "\n\n").encode("utf-8"))
                except queue.Empty:
                    self.wfile.write(b": keep-alive\n\n")
                self.wfile.flush()
        except OSError:
            pass
        finally:
            EMU.unsubscribe(q)

    def do_POST(self):
        if not self._host_ok() or self.headers.get("X-Keypad-Key") != SESSION_KEY:
            return self._send(403, "{}")
        length = int(self.headers.get("Content-Length", "0") or 0)
        try:
            msg = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self._send(400, "{}")
        if self.path == "/api/msg":
            return self._send(200, json.dumps(EMU.on_page_message(msg) or []))
        if self.path == "/api/open":
            ok = EMU.set_file(msg.get("file", ""))
            if ok and msg.get("run", True):
                EMU.run()
            return self._send(200, json.dumps({"ok": ok}))
        self._send(404, "{}")


# ======================================================================
# Startup
# ======================================================================

def bridge_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)

    def loop():
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=EMU.on_connection, args=(conn,), daemon=True).start()

    threading.Thread(target=loop, daemon=True).start()
    return srv.getsockname()[1]


def read_discovery():
    try:
        with open(DISCOVERY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def hand_off(file):
    """If an emulator is already open, send it the file and return True."""
    info = read_discovery()
    if not info:
        return False
    base = "http://127.0.0.1:%d" % int(info.get("http_port", 0))
    try:
        urllib.request.urlopen(base + "/api/ping", timeout=1).read()
    except (OSError, ValueError):
        return False
    if file:
        req = urllib.request.Request(
            base + "/api/open", data=json.dumps({"file": os.path.abspath(file)}).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Keypad-Key": info.get("key", "")})
        try:
            ok = json.loads(urllib.request.urlopen(req, timeout=3).read()).get("ok")
        except (OSError, ValueError):
            return False
        print("Sent %s to the open Pico Keypad Emulator." % os.path.basename(file) if ok
              else "The emulator could not find %s." % file)
    else:
        print("The Pico Keypad Emulator is already open:")
        print("  " + info.get("url", base))
        webbrowser.open(info.get("url", base))
    return True


def shutdown():
    time.sleep(0.2)
    EMU.stop(None)
    remove_discovery()
    os._exit(0)


def remove_discovery():
    info = read_discovery()
    if info and info.get("key") == SESSION_KEY:
        try:
            os.remove(DISCOVERY_FILE)
        except OSError:
            pass


def pth_dir():
    import site
    import sysconfig
    if site.ENABLE_USER_SITE and not hasattr(sys, "real_prefix") and sys.prefix == sys.base_prefix:
        return site.getusersitepackages()
    return sysconfig.get_paths()["purelib"]   # inside a virtual environment


def install(remove=False):
    d = pth_dir()
    target = os.path.join(d, PTH_NAME)
    if remove:
        if os.path.exists(target):
            os.remove(target)
            print("Removed " + target)
        else:
            print("Nothing to remove (%s not found)." % target)
        return
    os.makedirs(d, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(SHIM + "\n")
    print("Installed for this Python (%s):\n  %s" % (sys.executable, target))
    print("Programs run by your editor can now `import picokeypad` and will show on an\n"
          "open emulator window. Make sure your editor uses this same Python.")


def main():
    global BRIDGE_PORT, HTTP_PORT, HTTPD
    ap = argparse.ArgumentParser(description="Pico RGB Keypad Emulator (standalone)")
    ap.add_argument("file", nargs="?", help="program to run, e.g. main.py")
    ap.add_argument("--install", action="store_true", help="let editor-run programs use the emulator")
    ap.add_argument("--uninstall", action="store_true", help="undo --install")
    ap.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    ap.add_argument("--port", type=int, default=0, help="web page port (default: any free port)")
    args = ap.parse_args()

    if sys.version_info < (3, 8):
        sys.exit("The keypad emulator needs Python 3.8 or newer.")
    if args.install or args.uninstall:
        install(remove=args.uninstall)
        return
    if args.file and not os.path.isfile(args.file):
        sys.exit("File not found: " + args.file)
    if hand_off(args.file):
        return

    BRIDGE_PORT = bridge_server()
    HTTPD = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    HTTPD.daemon_threads = True
    HTTP_PORT = HTTPD.server_address[1]
    url = "http://127.0.0.1:%d/?k=%s" % (HTTP_PORT, SESSION_KEY)

    info = {"http_port": HTTP_PORT, "bridge_port": BRIDGE_PORT, "key": SESSION_KEY,
            "attach_token": EMU.attach_token, "url": url, "pid": os.getpid()}
    with open(DISCOVERY_FILE, "w", encoding="utf-8") as f:
        json.dump(info, f)
    try:
        os.chmod(DISCOVERY_FILE, 0o600)
    except OSError:
        pass

    threading.Thread(target=EMU.watch, daemon=True).start()
    print("Pico RGB Keypad Emulator is running at\n  %s\n"
          "Keep this window open while you work. Press Ctrl+C to quit.\n" % url, flush=True)
    if args.file:
        EMU.set_file(args.file)
        EMU.run()
    if not args.no_browser:
        webbrowser.open(url)
    try:
        HTTPD.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        EMU.stop(None)
        remove_discovery()


if __name__ == "__main__":
    main()
