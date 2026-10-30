"use strict";
/*
 * Moteur de l'atelier. Un sprite est une pile de calques ; chaque pixel porte un
 * JETON, jamais une couleur : « famille.ton » (plante.b, metal.hi…), « etat-actif.hi »
 * pour un voyant, ou « #rrggbb » pour une copie fidèle d'un sprite actuel.
 * Les tons d'une famille : hi (reflet), b (base), s (ombre), d (creux), bl (joue).
 * Le contour sélectif devient « famille.ol », le liseré de lumière « famille.ton~r ».
 * Le mode (jour, nuit) ne change que la résolution jeton → couleur : c'est ce que
 * feraient des variables CSS dans Tessera.
 */

/* ---------- Couleurs ---------- */
const h2r = h => { h = h.replace("#", ""); return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16)); };
const r2h = (r, g, b) => "#" + [r, g, b].map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("");
function toHsl(hex) {
  const [r, g, b] = h2r(hex).map(v => v / 255);
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2;
  if (mx === mn) return [0, 0, l];
  const d = mx - mn, s = l > .5 ? d / (2 - mx - mn) : d / (mx + mn);
  const h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h * 60, s, l];
}
function fromHsl(h, s, l) {
  s = Math.max(0, Math.min(1, s)); l = Math.max(0, Math.min(1, l));
  const k = n => (n + h / 30) % 12, a = s * Math.min(l, 1 - l);
  const f = n => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return r2h(f(0) * 255, f(8) * 255, f(4) * 255);
}
const mix = (a, b, t) => { const x = h2r(a), y = h2r(b); return r2h(...x.map((v, i) => v + (y[i] - v) * t)); };
const toward = (h, t, amt) => { const d = ((t - h + 540) % 360) - 180; return (h + d * amt + 360) % 360; };
/** La rampe d'une base ; `k` < 1 resserre les écarts (grandes surfaces sombres) : reflet vers le jaune, ombres vers le bleu (glissement de teinte). */
function ramp(hex, k = 1) {
  const [h, s, l] = toHsl(hex);
  return {
    hi: fromHsl(toward(h, 55, .14 * k), s * .95, l + .13 * k),
    b: hex,
    s: fromHsl(toward(h, 250, .12 * k), s * 1.05 + .03 * k, l - .11 * k),
    d: fromHsl(toward(h, 250, .2 * k), s * 1.05 + .05 * k, l - .21 * k),
    bl: mix(hex, "#e0605a", .32),
  };
}
const selout = hex => { const [h, s, l] = toHsl(hex); return fromHsl(toward(h, 250, .25), s, l * .42); };

/* ---------- Grille ---------- */
class G {
  constructor(w, h) { this.w = w; this.h = h; this.p = new Array(w * h).fill(null); this.n = 0; }
  set(x, y, c) { if (x >= 0 && y >= 0 && x < this.w && y < this.h) this.p[y * this.w + x] = c; }
  get(x, y) { return x < 0 || y < 0 || x >= this.w || y >= this.h ? null : this.p[y * this.w + x]; }
  rect(x, y, w, h, c) { this.n++; for (let j = y; j < y + h; j++) for (let i = x; i < x + w; i++) this.set(i, j, c); }
  px(x, y, c) { this.n++; this.set(x, y, c); }
  clr(x, y) { this.set(x, y, null); }
  /** Une ligne de pixels, de (x0, y0) à (x1, y1), tracée à la Bresenham. */
  line(x0, y0, x1, y1, c) {
    this.n++;
    const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    let e = dx + dy;
    for (;;) { this.set(x0, y0, c); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 >= dy) { e += dy; x0 += sx; } if (e2 <= dx) { e += dx; y0 += sy; } }
  }
  /** Un disque plein, ombré par sa position : reflet en haut à gauche, ombre en bas à droite. */
  disc(cx, cy, r, fam, { shade = true } = {}) {
    this.n++;
    for (let y = Math.floor(cy - r); y <= cy + r; y++) for (let x = Math.floor(cx - r); x <= cx + r; x++) {
      const dx = x - cx, dy = y - cy, d2 = dx * dx + dy * dy;
      if (d2 > r * r + .6) continue;
      if (!shade) { this.set(x, y, fam + ".b"); continue; }
      const t = (dx + dy) / r;
      let ton = t < -.75 ? "hi" : t < .35 ? "b" : "s";
      if (d2 > (r - 1) * (r - 1) + .6 && t > .3) ton = "d";
      this.set(x, y, fam + "." + ton);
    }
  }
  /** Un motif texte : chaque caractère renvoie à un jeton par `map`, « . » est vide. */
  stamp(x, y, rows, map) { this.n++; rows.forEach((r, j) => [...r].forEach((ch, i) => { if (ch !== "." && ch !== " " && map[ch] !== undefined) this.set(x + i, y + j, map[ch]); })); }
}
function mk(w, h) {
  const s = { w, h, layers: [] };
  s.L = (cls = "", style = "") => { const g = new G(w, h); s.layers.push({ g, cls, style }); return g; };
  return s;
}
const occupied = (s, x, y) => s.layers.some(l => l.g.get(x, y));
const famille = tok => tok.startsWith("#") ? null : tok.split(".")[0];

/**
 * Le traitement de build : liseré de lumière (marqué « ~r », appliqué seulement si le
 * mode le demande) puis contour sélectif (« famille.ol »). Les jetons « etat-* » et les
 * couleurs fixes n'en reçoivent pas : un voyant garde sa teinte.
 */
function bake(s, { outline = true, rim = true } = {}) {
  if (rim) for (const { g } of s.layers) {
    const src = g.p.slice();
    for (let y = 0; y < s.h; y++) for (let x = 0; x < s.w; x++) {
      const c = src[y * s.w + x];
      if (c && !c.startsWith("#") && !c.startsWith("etat") && !c.endsWith(".ol") && (!occupied(s, x - 1, y) || !occupied(s, x, y - 1))) g.set(x, y, c + "~r");
    }
  }
  if (outline) for (const { g } of s.layers) {
    const src = g.p.slice(), at = (x, y) => x < 0 || y < 0 || x >= s.w || y >= s.h ? null : src[y * s.w + x];
    for (let y = 0; y < s.h; y++) for (let x = 0; x < s.w; x++) {
      if (occupied(s, x, y)) continue;
      const n = at(x - 1, y) || at(x + 1, y) || at(x, y - 1) || at(x, y + 1);
      if (!n) continue;
      const f = famille(n.replace("~r", ""));
      if (f && !f.startsWith("etat")) g.set(x, y, f + ".ol");
    }
  }
  return s;
}

/* ---------- Rendu ---------- */
/** `resolve(jeton)` → couleur. Un path par jeton : c'est le coût réel dans le DOM. */
function toSvg(s, dw, dh, resolve, extra = "") {
  let body = "", nodes = 0, pixels = 0;
  for (const { g, cls, style } of s.layers) {
    const byTok = new Map();
    for (let y = 0; y < s.h; y++) {
      let x = 0;
      while (x < s.w) {
        const c = g.p[y * s.w + x];
        if (!c) { x++; continue; }
        let e = x; while (e < s.w && g.p[y * s.w + e] === c) e++;
        byTok.set(c, (byTok.get(c) || "") + `M${x} ${y}h${e - x}v1h${x - e}z`);
        pixels += e - x; x = e;
      }
    }
    let inner = "";
    for (const [t, d] of byTok) { inner += `<path fill="${resolve(t)}" d="${d}"/>`; nodes++; }
    body += cls || style ? `<g class="${cls}" style="${style}">${inner}</g>` : inner;
  }
  return { html: `<svg class="px" viewBox="0 0 ${s.w} ${s.h}" width="${dw}" height="${dh}" shape-rendering="crispEdges" overflow="visible" ${extra}>${body}</svg>`, nodes, pixels };
}
const rectCount = s => s.layers.reduce((n, l) => n + l.g.n, 0);
function flatten(s) { const g = new G(s.w, s.h); for (const l of s.layers) l.g.p.forEach((c, i) => { if (c) g.p[i] = c; }); const o = mk(s.w, s.h); o.layers.push({ g, cls: "", style: "" }); return o; }
