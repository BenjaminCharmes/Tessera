// Construit les pages : chaque pages/<nom>.html reçoit, à la place de <!-- SOURCES -->,
// toutes les sources puis pages/<nom>.js, en ligne. Sortie : dist/<nom>.html.
const fs = require("fs");
const path = require("path");
const { RACINE, sources } = require("./sources");

const dist = path.join(RACINE, "dist");
fs.mkdirSync(dist, { recursive: true });
const commun = sources().map(f => `// ${path.relative(RACINE, f).replace(/\\/g, "/")}\n${fs.readFileSync(f, "utf8")}`).join("\n");
for (const f of fs.readdirSync(path.join(RACINE, "pages")).filter(f => f.endsWith(".html"))) {
  const nom = f.replace(/\.html$/, "");
  const gabarit = fs.readFileSync(path.join(RACINE, "pages", f), "utf8");
  const pageJs = path.join(RACINE, "pages", nom + ".js");
  const propre = fs.existsSync(pageJs) ? fs.readFileSync(pageJs, "utf8") : "";
  const dossierCss = path.join(RACINE, "pages", "css");
  const lots = fs.existsSync(dossierCss) ? fs.readdirSync(dossierCss).filter(f => f.endsWith(".css")).sort().map(f => fs.readFileSync(path.join(dossierCss, f), "utf8")) : [];
  const css = [fs.readFileSync(path.join(RACINE, "pages", "commun.css"), "utf8"), ...lots].join("\n");
  const sortie = gabarit
    .replace("/* COMMUN_CSS */", () => css)
    .replace("<!-- SOURCES -->", () => `<script>\n${commun}\n// pages/${nom}.js\n${propre}\n</script>`);
  fs.writeFileSync(path.join(dist, f), sortie);
  console.log(`dist/${f} (${(sortie.length / 1024).toFixed(0)} Ko)`);
}
