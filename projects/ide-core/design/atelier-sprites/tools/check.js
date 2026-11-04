// Contrôle : charge toutes les sources, dessine chaque sprite du registre dans les deux modes
// et signale erreurs, familles inconnues, sprites vides ou débordant de leur grille.
// Usage : node tools/check.js [id…]
const fs = require("fs");
const vm = require("vm");
const { sources } = require("./sources");

const ctx = vm.createContext({ console, Math, JSON, Object, Array, Map, Set, String, Number });
for (const f of sources()) vm.runInContext(fs.readFileSync(f, "utf8"), ctx, { filename: f });
vm.runInContext("this.__R = REGISTRE; this.__ctx = { bake, toSvg, resolveur, FAMILLES, rectCount };", ctx);
const REG = ctx.__R, { bake, toSvg, resolveur, FAMILLES, rectCount } = ctx.__ctx;
const filtre = process.argv.slice(2);
const jour = resolveur("jour"), nuit = resolveur("nuit");
let erreurs = 0;
const ids = new Set();
for (const def of REG) {
  if (filtre.length && !filtre.includes(def.id)) continue;
  const pb = [];
  if (ids.has(def.id)) pb.push("id en double"); ids.add(def.id);
  for (const k of ["id", "nom", "fichier", "salle", "grille", "dw", "dh", "apres", "note"]) if (def[k] === undefined) pb.push(`champ manquant : ${k}`);
  const essais = [["apres", def.apres]];
  if (def.avant) essais.push(["avant", def.avant]);
  if (def.meme) essais.push(["meme", def.meme]);
  if (def.variante) essais.push(["variante", def.variante.f]);
  let stats = "";
  for (const [nom, fn] of essais) {
    let s;
    try { s = fn(); } catch (e) { pb.push(`${nom} : ${e.message}`); continue; }
    if (!s || !s.layers) { pb.push(`${nom} : ne renvoie pas un sprite`); continue; }
    const toks = new Set();
    s.layers.forEach(l => l.g.p.forEach(t => t && toks.add(t)));
    if (!toks.size) pb.push(`${nom} : sprite vide`);
    for (const t of toks) {
      if (t.startsWith("#")) { if (nom === "apres" || nom === "variante") pb.push(`${nom} : couleur fixe ${t} (utiliser une famille)`); continue; }
      const [fam, ton] = t.split("^")[0].replace("~r", "").split(".");
      if (!fam.startsWith("etat-") && !FAMILLES[fam]) pb.push(`${nom} : famille inconnue « ${fam} »`);
      if (!["hi", "b", "s", "d", "bl", "ol"].includes(ton)) pb.push(`${nom} : ton inconnu « ${t} »`);
    }
    if (nom === "apres") {
      const b = bake(s, { outline: true, rim: true });
      const j = toSvg(b, def.dw, def.dh, jour), n = toSvg(b, def.dw, def.dh, nuit);
      stats = `${s.w}×${s.h}, ${n.nodes} paths, ${n.pixels} px`;
      if (j.html.includes("#ff00ff") || n.html.includes("#ff00ff")) pb.push("apres : couleur introuvable (#ff00ff)");
      const ratio = (s.w / s.h) / (def.dw / def.dh);
      if (Math.abs(ratio - 1) > .02) pb.push(`apres : proportions ${s.w}×${s.h} ≠ affichage ${def.dw}×${def.dh}`);
    }
    if (nom === "avant") stats += ` · avant ${rectCount(s)} rect`;
  }
  const dedoublonne = [...new Set(pb)];
  if (dedoublonne.length) { erreurs++; console.log(`✗ ${def.id} — ${dedoublonne.join(" ; ")}`); }
  else console.log(`✓ ${def.id} (${stats})`);
}
console.log(`\n${REG.length} sprites, ${erreurs} en erreur`);
process.exit(erreurs ? 1 : 0);
