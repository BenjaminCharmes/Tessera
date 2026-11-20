// Le thème CSS des sprites pour Tessera (ticket-727) : une variable par famille × ton,
// jour sous `@theme static`, nuit sous `[data-moment="nuit"]`. L'atelier reste la
// source des couleurs ; Tessera ne fait que lire ce fichier.
// Usage : node tools/theme.js <chemin de sortie>
const fs = require("fs");
const vm = require("vm");
const { sources } = require("./sources");

const ctx = vm.createContext({ console, Math, JSON, Object, Array, Map, Set, String, Number });
for (const f of sources()) vm.runInContext(fs.readFileSync(f, "utf8"), ctx, { filename: f });
vm.runInContext("this.__x = { resolveur, FAMILLES, ETATS };", ctx);
const { resolveur, FAMILLES, ETATS } = ctx.__x;

// Le blond clair de l'équipe nommée de Tessera n'est jamais tiré au sort : l'atelier
// ne le dessine pas, Tessera le porte (`--sprite-cheveux-7`).
FAMILLES.cheveux7 = FAMILLES.cheveux7 || { tessera: "#d6a84a" };

const TONS = ["hi", "b", "s", "d", "bl", "ol"];
const familles = [...Object.keys(FAMILLES).sort(), ...Object.keys(ETATS).map(e => "etat-" + e)];

function bloc(mode) {
  const r = resolveur(mode);
  return familles.flatMap(f => TONS.map(t => `  --sprite-${f}-${t}: ${r(`${f}.${t}`)};`)).join("\n");
}

const css = `/*
 * Les couleurs des sprites du Bureau — GÉNÉRÉ par atelier-sprites/tools/theme.js,
 * ne pas éditer à la main (ticket-727). Une variable par famille × ton ; la nuit les
 * redéfinit, avec le liseré de lumière et la lueur des écrans.
 */
@theme static {
${bloc("jour")}
  --sprite-lisere: #5ef2ff;
  --sprite-lisere-force: 0;
  --sprite-lueur-force: 0;
}

[data-moment="nuit"] {
${bloc("nuit")}
  --sprite-lisere-force: 0.38;
  --sprite-lueur-force: 1;
}
`;
const sortie = process.argv[2];
if (!sortie) { process.stdout.write(css); process.exit(0); }
fs.writeFileSync(sortie, css);
console.log(`${familles.length} familles, ${familles.length * TONS.length} variables → ${sortie}`);
