import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Verrou d'identité — ticket-100.
 *
 * ticket-099 a renommé le produit partout où le nom s'écrivait. Il n'a rien
 * changé ici, et pour une raison qui se répétera : aucun de ces fichiers ne
 * contenait l'ancien nom. Ils portaient le nom du dossier de build. Une
 * substitution en masse ne voit pas un défaut générique, seulement un défaut
 * nommé.
 *
 * Ces tests sont la mesure. Le titre de l'onglet et le nom du paquet sont les
 * deux endroits où « frontend » revient tout seul, à la première régénération
 * d'un scaffold.
 */
const RACINE = join(__dirname, "..", "..");

const INDEX = readFileSync(join(RACINE, "index.html"), "utf-8");
const PACKAGE = readFileSync(join(RACINE, "package.json"), "utf-8");
const FAVICON = readFileSync(join(RACINE, "public", "favicon.svg"), "utf-8");

/** Le violet du template d'origine, qui n'a jamais appartenu au projet. */
const VIOLET_DU_TEMPLATE = "#863bff";

describe("identité visible", () => {
  it("annonce Tessera dans l'onglet du navigateur", () => {
    // Panne vécue : l'onglet affichait « frontend » — le nom du dossier, pas
    // celui du produit — pendant les cent premiers tickets.
    expect(INDEX).toContain("<title>Tessera</title>");
    expect(INDEX).not.toMatch(/<title>\s*frontend\s*<\/title>/i);
  });

  it("nomme le paquet d'après le produit, pas d'après le dossier", () => {
    const manifeste = JSON.parse(PACKAGE) as { name: string };
    expect(manifeste.name).toBe("tessera");
  });

  it("ne sert plus le logo du template", () => {
    expect(FAVICON.toLowerCase()).not.toContain(VIOLET_DU_TEMPLATE);
  });

  it("dessine la marque dans les deux thèmes", () => {
    // ADR-026 : le violet porte l'identité. Une icône monochrome posée sur
    // fond sombre y perd ses tesselles en retrait, qui sont ce qui distingue
    // la marque d'un carré.
    expect(FAVICON).toContain("prefers-color-scheme: dark");
  });
});
