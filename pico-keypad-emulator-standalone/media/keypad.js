// Keypad panel: draws the 16 pads, turns mouse / touch / keyboard input into
// the 16-bit button mask, and shows the LED colours sent by the program.
(function () {
  'use strict';

  const vscode = acquireVsCodeApi();
  const app = document.getElementById('app');
  const options = JSON.parse(app.dataset.options || '{}');

  const grid = document.getElementById('grid');
  const statusEl = document.getElementById('status');
  const fileEl = document.getElementById('file');
  const errorEl = document.getElementById('error');
  const runBtn = document.getElementById('run');
  const stopBtn = document.getElementById('stop');
  const maskBin = document.getElementById('mask-bin');
  const maskDec = document.getElementById('mask-dec');
  const brightEl = document.getElementById('bright');
  const picoLedEl = document.getElementById('picoled');

  const KEYS = ['1', '2', '3', '4', 'q', 'w', 'e', 'r', 'a', 's', 'd', 'f', 'z', 'x', 'c', 'v'];
  const STATUS_TEXT = {
    idle: 'Idle', starting: 'Starting…', running: 'Running',
    finished: 'Finished', stopped: 'Stopped', error: 'Error',
  };

  // ---------------------------------------------------------------- pads

  const pads = [];
  for (let i = 0; i < 16; i++) {
    const pad = document.createElement('div');
    pad.className = 'pad';
    pad.dataset.index = String(i);
    pad.setAttribute('role', 'gridcell');
    pad.setAttribute('aria-label', 'Pad ' + i);
    if (options.showPadNumbers !== false) {
      const n = document.createElement('span');
      n.className = 'num';
      n.textContent = String(i);
      pad.appendChild(n);
    }
    grid.appendChild(pad);
    pads.push(pad);
  }
  grid.tabIndex = 0;
  if (options.keyboard === false) {
    const kb = document.getElementById('kb-help');
    if (kb) kb.remove();
  }

  // ---------------------------------------------------------------- input

  const pointerPads = new Map(); // pointerId -> pad index
  const keyPads = new Set();     // pad indices held by keyboard
  let latched = 0;
  let mask = 0;

  function recompute() {
    let m = latched;
    for (const i of pointerPads.values()) m |= 1 << i;
    for (const i of keyPads) m |= 1 << i;
    m &= 0xffff;
    for (let i = 0; i < 16; i++) {
      pads[i].classList.toggle('pressed', !!(m & (1 << i)));
      pads[i].classList.toggle('latched', !!(latched & (1 << i)));
    }
    if (m !== mask) {
      mask = m;
      vscode.postMessage({ type: 'buttons', value: m });
      showMask(m);
    }
  }

  function showMask(m) {
    const bits = m.toString(2).padStart(16, '0');
    maskBin.textContent = '0b';
    for (const ch of bits) {
      const s = document.createElement('span');
      s.textContent = ch;
      if (ch === '1') s.className = 'one';
      maskBin.appendChild(s);
    }
    maskDec.textContent = '(' + m + ')';
  }

  function padIndex(target) {
    const pad = target && target.closest ? target.closest('.pad') : null;
    return pad ? parseInt(pad.dataset.index, 10) : -1;
  }

  grid.addEventListener('pointerdown', (e) => {
    const i = padIndex(e.target);
    if (i < 0) return;
    e.preventDefault();
    grid.focus({ preventScroll: true });
    if (e.button === 2 || (e.button === 0 && e.shiftKey)) {
      latched ^= 1 << i; // right-click / shift-click latches a pad down
      recompute();
      return;
    }
    if (e.button !== 0) return;
    try { e.target.setPointerCapture(e.pointerId); } catch { /* ignore */ }
    pointerPads.set(e.pointerId, i);
    recompute();
  });

  const release = (e) => {
    if (pointerPads.delete(e.pointerId)) recompute();
  };
  grid.addEventListener('pointerup', release);
  grid.addEventListener('pointercancel', release);
  grid.addEventListener('lostpointercapture', release);
  grid.addEventListener('contextmenu', (e) => e.preventDefault());

  if (options.keyboard !== false) {
    grid.addEventListener('keydown', (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const i = KEYS.indexOf(e.key.toLowerCase());
      if (i < 0) return;
      e.preventDefault();
      if (!keyPads.has(i)) { keyPads.add(i); recompute(); }
    });
    grid.addEventListener('keyup', (e) => {
      const i = KEYS.indexOf(e.key.toLowerCase());
      if (i >= 0 && keyPads.delete(i)) recompute();
    });
  }

  // Never leave a pad stuck down when the panel loses focus.
  window.addEventListener('blur', () => {
    if (pointerPads.size || keyPads.size) {
      pointerPads.clear();
      keyPads.clear();
      recompute();
    }
  });

  runBtn.addEventListener('click', () => vscode.postMessage({ type: 'run' }));
  stopBtn.addEventListener('click', () => vscode.postMessage({ type: 'stop' }));

  // ---------------------------------------------------------------- output

  // The LEDs are driven by PWM, so their light output is linear in the value
  // sent. Screens are not (sRGB), so encode with a ~2.2 gamma to make, say,
  // illuminate(i, 32, 0, 0) look about as visible as it does on the device.
  function toScreen(v, brightness) {
    const lin = Math.max(0, Math.min(1, (v / 255) * brightness));
    return Math.round(255 * Math.pow(lin, 1 / 2.2));
  }

  let pending = null;
  function drawLeds(leds, brightness, picoLed) {
    pending = { leds, brightness, picoLed };
    requestAnimationFrame(flush);
  }

  function flush() {
    if (!pending) return;
    const { leds, brightness, picoLed } = pending;
    pending = null;
    for (let i = 0; i < 16; i++) {
      const [r0, g0, b0] = leds[i] || [0, 0, 0];
      const r = toScreen(r0, brightness);
      const g = toScreen(g0, brightness);
      const b = toScreen(b0, brightness);
      const pad = pads[i];
      const max = Math.max(r, g, b);
      if (max < 6) {
        pad.classList.remove('lit');
        continue;
      }
      // Bright centre (LED hot-spot) fading to the colour at the edge.
      const core = `rgb(${mix(r, 255, 0.45)},${mix(g, 255, 0.45)},${mix(b, 255, 0.45)})`;
      const edge = `rgb(${Math.round(r * 0.72)},${Math.round(g * 0.72)},${Math.round(b * 0.72)})`;
      pad.style.setProperty('--c', `rgb(${r},${g},${b})`);
      pad.style.setProperty('--core', max > 40 ? core : `rgb(${r},${g},${b})`);
      pad.style.setProperty('--edge', edge);
      pad.style.setProperty('--glow', Math.round(4 + (max / 255) * 18) + 'px');
      const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      pad.style.setProperty('--numc', lum > 140 ? 'rgba(0,0,0,.5)' : 'rgba(255,255,255,.7)');
      pad.classList.add('lit');
    }
    picoLedEl.classList.toggle('on', !!picoLed);
    brightEl.textContent = Number(brightness).toFixed(2);
  }

  function mix(a, b, t) {
    return Math.round(a + (b - a) * t * (a / 255));
  }

  function setStatus(status, error, file) {
    statusEl.className = 'status ' + status;
    statusEl.textContent = STATUS_TEXT[status] || status;
    const running = status === 'running' || status === 'starting';
    stopBtn.disabled = !running;
    runBtn.textContent = running ? '↻ Restart' : '▶ Run';
    fileEl.textContent = file ? file : 'Open a .py file and press Run';
    if (error) {
      errorEl.textContent = error;
      errorEl.hidden = false;
    } else {
      errorEl.hidden = true;
    }
  }

  window.addEventListener('message', (event) => {
    const msg = event.data;
    if (msg.type === 'state') {
      setStatus(msg.status, msg.error, msg.file);
      drawLeds(msg.leds, msg.brightness, msg.picoLed);
    } else if (msg.type === 'leds') {
      drawLeds(msg.leds, msg.brightness, msg.picoLed);
    }
  });

  showMask(0);
  setStatus('idle', null, null);
  vscode.postMessage({ type: 'ready' });
  // Tell the extension the current mask in case the panel was reloaded.
  vscode.postMessage({ type: 'buttons', value: 0 });
})();
