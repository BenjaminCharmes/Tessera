// Capture les écrans d'un projet lancé — ticket-432.
//
// Lancé par le backend (services/captures.py) : la configuration arrive en
// JSON sur stdin, le dossier de sortie en premier argument. Le Playwright
// utilisé est celui du frontend de Tessera, déjà installé pour les tests de
// bout en bout ; `scripts/` ne résout pas `frontend/node_modules`, d'où le
// require ancré sur `frontend/package.json`.
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(join(racine, "frontend", "package.json"));
const { chromium } = require("@playwright/test");

const HAUTEUR = { 390: 844, 1440: 900 };
const SCHEMA = { clair: "light", sombre: "dark" };

async function capturer(navigateur, config, sortie, largeur, theme, ecran) {
  const contexte = await navigateur.newContext({
    viewport: { width: largeur, height: HAUTEUR[largeur] ?? 900 },
    colorScheme: SCHEMA[theme],
  });
  try {
    const page = await contexte.newPage();
    await page.goto(config.url + ecran.chemin, { waitUntil: "networkidle" });
    if (ecran.clic) {
      await page.getByText(ecran.clic, { exact: true }).first().click();
      await page.waitForLoadState("networkidle");
    }
    const fichier = `${ecran.nom}-${largeur}-${theme}.png`;
    await page.screenshot({ path: join(sortie, fichier), fullPage: true });
  } finally {
    await contexte.close();
  }
}

async function main() {
  const sortie = process.argv[2];
  if (!sortie) throw new Error("Dossier de sortie manquant.");
  const config = JSON.parse(readFileSync(0, "utf-8"));
  const navigateur = await chromium.launch();
  try {
    for (const ecran of config.ecrans) {
      for (const largeur of config.largeurs) {
        for (const theme of config.themes) {
          await capturer(navigateur, config, sortie, largeur, theme, ecran);
        }
      }
    }
  } finally {
    await navigateur.close();
  }
}

main().catch((erreur) => {
  process.stderr.write(`${erreur instanceof Error ? erreur.message : erreur}\n`);
  process.exit(1);
});
