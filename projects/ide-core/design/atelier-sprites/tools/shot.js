// Capture d'une page de dist/ avec le Playwright du frontend de Tessera (rien n'est installé ici).
// Usage : node tools/shot.js <page.html> <sortie.png> [sélecteur] [largeur]
const path = require("path");
const { chromium } = require("C:/Users/Benjamin.CHARMES/Desktop/tessera/frontend/node_modules/playwright");
(async () => {
  const [page, out, sel, w] = process.argv.slice(2);
  const b = await chromium.launch(), p = await b.newPage({ viewport: { width: +(w || 1280), height: 900 } });
  const errs = [];
  p.on("pageerror", e => errs.push(e.message)); p.on("console", m => m.type() === "error" && errs.push(m.text()));
  await p.goto("file:///" + path.resolve(__dirname, "..", "dist", page).split(path.sep).join("/"));
  await p.waitForTimeout(600);
  if (sel) await (await p.$(sel)).screenshot({ path: out }); else await p.screenshot({ path: out, fullPage: true });
  console.log(errs.length ? "ERREURS : " + JSON.stringify(errs) : "aucune erreur");
  await b.close();
})();
