import { describe, expect, it } from "vitest";
import { LONGUEUR_MAX_DE_LA_PHRASE, phraseDOutil, tronquer } from "./phraseDOutil";

describe("phraseDOutil", () => {
  it("says which file is read, without its path", () => {
    const entree = { file_path: "C:\\Users\\jdupont\\projets\\ide-core\\backend\\conflits.py" };

    expect(phraseDOutil("Read", entree)).toBe("lit conflits.py");
  });

  it("keeps only the file name of a POSIX path", () => {
    expect(phraseDOutil("NotebookRead", { notebook_path: "/home/ada/analyse.ipynb" })).toBe("lit analyse.ipynb");
  });

  it("says edit for Edit, Write and MultiEdit", () => {
    for (const outil of ["Edit", "Write", "MultiEdit"]) {
      expect(phraseDOutil(outil, { file_path: "src/components/Piece.tsx" })).toBe("édite Piece.tsx");
    }
  });

  it("names the program a Bash command runs after uv run", () => {
    expect(phraseDOutil("Bash", { command: "uv run pytest -q" })).toBe("lance pytest");
  });

  it("skips npx and npm run launchers and their options", () => {
    expect(phraseDOutil("Bash", { command: "npx --yes vitest run" })).toBe("lance vitest");
    expect(phraseDOutil("Bash", { command: "npm run lint" })).toBe("lance lint");
  });

  it("does not stop at a leading cd", () => {
    expect(phraseDOutil("Bash", { command: "cd frontend && npx tsc --noEmit" })).toBe("lance tsc");
  });

  it("keeps the program name of a command given by path", () => {
    expect(phraseDOutil("Bash", { command: "python scripts/verifier.py" })).toBe("lance python");
    expect(phraseDOutil("Bash", { command: "./scripts/verifier.py" })).toBe("lance verifier.py");
  });

  it("falls back on a generic phrase for an empty command", () => {
    expect(phraseDOutil("Bash", { command: "  " })).toBe("lance une commande");
    expect(phraseDOutil("Bash", {})).toBe("lance une commande");
  });

  it("quotes the pattern of Grep and Glob", () => {
    expect(phraseDOutil("Grep", { pattern: "santeAgent" })).toBe('cherche "santeAgent"');
    expect(phraseDOutil("Glob", { pattern: "**/*.tsx" })).toBe('cherche "**/*.tsx"');
  });

  it("falls back on the tool name when the input says nothing usable", () => {
    expect(phraseDOutil("WebFetch", { url: "https://exemple.test" })).toBe("utilise WebFetch");
    expect(phraseDOutil("Read", {})).toBe("utilise Read");
    expect(phraseDOutil("Grep", { pattern: 3 })).toBe("utilise Grep");
  });

  it("truncates a phrase longer than 32 characters with an ellipsis", () => {
    const phrase = phraseDOutil("Read", { file_path: "src/un-nom-de-fichier-vraiment-tres-long.tsx" });

    expect(phrase).toHaveLength(LONGUEUR_MAX_DE_LA_PHRASE);
    expect(phrase.endsWith("…")).toBe(true);
    expect(phrase.startsWith("lit un-nom-de-fichier")).toBe(true);
  });
});

describe("tronquer", () => {
  it("leaves a phrase of exactly 32 characters alone", () => {
    const phrase = "a".repeat(LONGUEUR_MAX_DE_LA_PHRASE);

    expect(tronquer(phrase)).toBe(phrase);
  });

  it("cuts one character past the limit", () => {
    const resultat = tronquer("a".repeat(LONGUEUR_MAX_DE_LA_PHRASE + 1));

    expect(resultat).toBe(`${"a".repeat(LONGUEUR_MAX_DE_LA_PHRASE - 1)}…`);
  });
});
