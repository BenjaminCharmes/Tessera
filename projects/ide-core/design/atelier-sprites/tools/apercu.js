// Aperçu de quelques sprites : avant / jour / nuit à ×3, dans une page à part, puis capture PNG.
// Usage : node tools/apercu.js <sortie.png> <id> [id…]
// Chaque appel écrit sa propre page (dist/apercu-<horodatage>.html) : plusieurs agents peuvent travailler en même temps.
const fs = require("fs");
const path = require("path");
const { RACINE, sources } = require("./sources");
const { chromium } = require("C:/Users/Benjamin.CHARMES/Desktop/tessera/frontend/node_modules/playwright");

const [sortie, ...ids] = process.argv.slice(2);
if (!sortie || !ids.length) { console.error("usage : node tools/apercu.js <sortie.png> <id> [id…]"); process.exit(2); }
const code = sources().map(f => fs.readFileSync(f, "utf8")).join("\n");
const page = `<!doctype html><meta charset="utf-8"><style>
body{background:#141217;color:#eee;font:13px monospace;margin:16px}
.row{display:flex;gap:12px;align-items:flex-end;margin-bottom:18px;flex-wrap:wrap}
.t{display:flex;flex-direction:column;gap:4px}.s{padding:12px;display:flex;align-items:flex-end;gap:8px}
svg{display:block}</style><div id="out"></div><script>${code}
const out = document.getElementById("out"), ids = ${JSON.stringify(ids)};
for (const id of ids) {
  const def = sprite(id);
  if (!def) { out.insertAdjacentHTML("beforeend", "<p>introuvable : " + id + "</p>"); continue; }
  let h = '<div><b>' + id + '</b> — ' + def.nom + '</div><div class="row">';
  if (def.avant) h += '<div class="t"><div class="s" style="background:' + C.sol + '">' + rendre(def, { quoi: "avant", zoom: 3 }).html + '</div>avant</div>';
  for (const mode of ["jour", "nuit"]) h += '<div class="t"><div class="s" style="background:' + solDe(mode) + '">' + rendre(def, { mode, zoom: 3 }).html + '</div>' + mode + '</div>';
  if (def.variante) h += '<div class="t"><div class="s" style="background:' + solDe("jour") + '">' + rendre(def, { quoi: "variante", zoom: 3 }).html + '</div>variante</div>';
  out.insertAdjacentHTML("beforeend", h + "</div>");
}
</script>`;
const fichier = path.join(RACINE, "dist", `apercu-${Date.now()}-${process.pid}.html`);
fs.mkdirSync(path.dirname(fichier), { recursive: true });
fs.writeFileSync(fichier, page);
(async () => {
  const b = await chromium.launch(), p = await b.newPage({ viewport: { width: 1100, height: 800 } });
  const errs = [];
  p.on("pageerror", e => errs.push(e.message));
  await p.goto("file:///" + fichier.split(path.sep).join("/"));
  await p.screenshot({ path: sortie, fullPage: true });
  await b.close();
  fs.unlinkSync(fichier);
  console.log(errs.length ? "ERREURS : " + JSON.stringify(errs) : `capture : ${sortie}`);
})();
