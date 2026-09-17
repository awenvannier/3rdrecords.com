/* 3rdrecords.com — turntable scratch voice (AudioWorklet).
   The needle position follows the platter angle sent by site.js, so pitch, direction
   and loudness all come from how the record is moved, like on a real deck. */
class Scratch extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buf = null;       // Float32Array sample
    this.spd = 1;          // samples per degree of rotation
    this.p = 0;            // needle position (samples)
    this.t = 0;            // target position (samples)
    this.g = 0;            // output gain (fader)
    this.on = false;       // hand on the record
    this.follow = 1 - Math.exp(-1 / (sampleRate * 0.022));
    this.fade = 1 - Math.exp(-1 / (sampleRate * 0.01));
    this.port.onmessage = ({ data: m }) => {
      if (m.buf) { this.buf = m.buf; this.spd = m.spd; }
      if (typeof m.a === 'number') {
        this.t = m.a * this.spd;
        if (m.grab) this.p = this.t;
      }
      if (typeof m.on === 'boolean') this.on = m.on;
    };
  }

  process(_inputs, outputs) {
    const out = outputs[0];
    const L = out[0];
    const b = this.buf;
    if (!b || !L) return true;
    const N = b.length;
    for (let i = 0; i < L.length; i++) {
      const prev = this.p;
      this.p += (this.t - this.p) * this.follow;
      const rate = Math.abs(this.p - prev);            // 1 = normal speed
      const want = this.on ? Math.min(1, rate * 1.4) : 0;
      this.g += (want - this.g) * this.fade;
      const x = ((this.p % N) + N) % N;
      const i0 = x | 0, f = x - i0;
      const s = b[i0] + (b[(i0 + 1) % N] - b[i0]) * f;
      L[i] = s * this.g;
    }
    for (let c = 1; c < out.length; c++) out[c].set(L);
    return true;
  }
}
registerProcessor('scratch', Scratch);
