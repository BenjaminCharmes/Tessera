import { describe, it, expect } from "vitest";
import { adressesDansLaSortie } from "./adresse";

/** L'origine de l'IDE pendant ces tests — passée, jamais lue dans `window`. */
const IDE = "http://localhost:5173";

describe("adressesDansLaSortie", () => {
  it("trouve l'adresse que Vite annonce", () => {
    expect(
      adressesDansLaSortie(["  ➜  Local:   http://localhost:5174/"], IDE),
    ).toEqual([{ url: "http://localhost:5174/", etiquette: null }]);
  });

  it("trouve celle d'uvicorn", () => {
    expect(
      adressesDansLaSortie(
        ["INFO: Uvicorn running on http://127.0.0.1:8000"],
        IDE,
      ),
    ).toEqual([{ url: "http://127.0.0.1:8000", etiquette: null }]);
  });

  it("retient la derniere sous une meme etiquette : un serveur redemarre", () => {
    expect(
      adressesDansLaSortie(
        [
          "[web] Local: http://localhost:5174/",
          "[web] Port 5174 is in use, trying another one...",
          "[web] Local: http://localhost:5175/",
        ],
        IDE,
      ),
    ).toEqual([{ url: "http://localhost:5175/", etiquette: "web" }]);
  });

  // La sortie réelle de fluentdb, telle que le backend l'a conservée. Sa
  // dernière ligne est un log JSON qui *mentionne* un port dans une phrase :
  // l'ancienne lecture en faisait l'adresse du service, et avalait le `"}`
  // fermant — le lien tombait sur about:blank#blocked (ticket-154).
  const FLUENTDB = [
    "[web]   ➜  Local:   http://localhost:5174/",
    "[web]   ➜  Network: use --host to expose",
    '[server] {"level":30,"msg":"Server listening at http://127.0.0.1:4983"}',
    '[server] {"level":30,"msg":"FluentDB ready on http://127.0.0.1:4983"}',
    '[server] {"level":30,"msg":"Web UI not built — run `npm run dev:web` and open http://localhost:5173"}',
  ];

  it("rend une adresse par etiquette sur la sortie reelle de fluentdb", () => {
    expect(adressesDansLaSortie(FLUENTDB, IDE)).toEqual([
      { url: "http://localhost:5174/", etiquette: "web" },
      { url: "http://127.0.0.1:4983", etiquette: "server" },
    ]);
  });

  it("ne rend jamais une URL portant guillemet ou accolade", () => {
    for (const { url } of adressesDansLaSortie(FLUENTDB, IDE)) {
      expect(url).not.toMatch(/["{}]/);
    }
  });

  it("ecarte l'origine de l'IDE, quel que soit le nom de l'hote", () => {
    // Un service ne peut pas ecouter sur le port que le frontend de Tessera
    // occupe : c'est justement pourquoi Vite en a change.
    expect(
      adressesDansLaSortie(
        [
          "open http://localhost:5173",
          "open http://127.0.0.1:5173/",
          "open http://[::1]:5173",
        ],
        IDE,
      ),
    ).toEqual([]);
  });

  it("garde le meme port sur un autre hote que l'IDE", () => {
    expect(
      adressesDansLaSortie(["listening on http://127.0.0.1:4983"], IDE),
    ).toEqual([{ url: "http://127.0.0.1:4983", etiquette: null }]);
  });

  it("rend une liste vide quand rien n'est annonce", () => {
    expect(adressesDansLaSortie(["npm warn config", ""], IDE)).toEqual([]);
  });
});
