// L'ordre de chargement des sources : moteur, palettes, jetons, copies d'avant, puis chaque fichier de sprites.
const fs = require("fs");
const path = require("path");
const RACINE = path.join(__dirname, "..");
function sources() {
  const sprites = fs.readdirSync(path.join(RACINE, "src", "sprites")).filter(f => f.endsWith(".js")).sort().map(f => path.join("src", "sprites", f));
  return ["src/engine.js", "src/palettes.js", "src/base.js", "src/avant.js", "src/rendu.js", ...sprites].map(f => path.join(RACINE, f));
}
module.exports = { RACINE, sources };
