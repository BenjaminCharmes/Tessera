// Cliquet sur la longueur des fichiers frontend (ticket-545) : aucun fichier
// ne grossit, aucun fichier nouveau ne dépasse le plafond général.
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

export const PLAFOND_GENERAL = 300;

// Fichiers qui dépassaient déjà le plafond général à l'ouverture du ticket-545 :
// chemin relatif à src -> taille maximale. Le cliquet ne remonte pas : un
// découpage baisse l'entrée (ou la retire sous 300 lignes), jamais l'inverse.
export const PLAFONDS: Record<string, number> = {
  "components/FilDuRun/index.tsx": 360,
  "components/Sidebar/CreateProjectModal.tsx": 309,
  "components/Sidebar/ImportProjectModal.tsx": 428,
  "components/Sidebar/TicketCard.tsx": 314,
  "components/Sidebar/TicketList.tsx": 309,
  "hooks/streamState.ts": 627,
  "hooks/useChat.ts": 336,
  "hooks/useCockpit.ts": 532,
  "hooks/useSupervision.ts": 385,
  "lib/api.ts": 315,
  "types/api.ts": 676,
};

const SOURCES = join(__dirname);

function estSource(nom: string): boolean {
  return /\.tsx?$/.test(nom) && !/\.test\.tsx?$/.test(nom);
}

function compterLignes(fichier: string): number {
  const lignes = readFileSync(fichier, "utf-8").split(/\r?\n/);
  if (lignes[lignes.length - 1] === "") lignes.pop();
  return lignes.length;
}

/** Map each non-test .ts/.tsx file under racine (relative POSIX path) to its line count. */
export function mesurer(racine: string, relatif = ""): Record<string, number> {
  const tailles: Record<string, number> = {};
  const dossier = relatif === "" ? racine : join(racine, relatif);
  for (const entree of readdirSync(dossier, { withFileTypes: true })) {
    const chemin = relatif === "" ? entree.name : `${relatif}/${entree.name}`;
    if (entree.isDirectory()) {
      Object.assign(tailles, mesurer(racine, chemin));
    } else if (estSource(entree.name)) {
      tailles[chemin] = compterLignes(join(racine, chemin));
    }
  }
  return tailles;
}

/** Return the failure message for one file, or null when it complies. */
export function verifierFichier(
  chemin: string,
  taille: number,
  plafonds: Record<string, number>,
): string | null {
  const plafond = plafonds[chemin] ?? PLAFOND_GENERAL;
  if (taille > plafond) {
    return (
      `${chemin} : ${taille} lignes, plafond ${plafond}. ` +
      "Découpe le fichier plutôt que de relever le plafond."
    );
  }
  if (chemin in plafonds && taille < plafond) {
    const cible =
      taille > PLAFOND_GENERAL
        ? `baisse le plafond à ${taille}`
        : "retire l'entrée de PLAFONDS";
    return (
      `${chemin} : ${taille} lignes, plafond ${plafond}. ` +
      `Le fichier a rétréci, ${cible} pour que le cliquet se resserre.`
    );
  }
  return null;
}

/** Check every measured file against its ceiling. Pure: no disk access. */
export function controler(
  tailles: Record<string, number>,
  plafonds: Record<string, number>,
): string[] {
  const messages: string[] = [];
  for (const [chemin, taille] of Object.entries(tailles)) {
    const message = verifierFichier(chemin, taille, plafonds);
    if (message !== null) messages.push(message);
  }
  for (const [chemin, plafond] of Object.entries(plafonds)) {
    if (!(chemin in tailles)) {
      messages.push(`${chemin} : fichier absent, plafond ${plafond}. Retire l'entrée de PLAFONDS.`);
    }
  }
  return messages;
}

describe("longueur des fichiers frontend", () => {
  it("respects every ceiling in src", () => {
    expect(controler(mesurer(SOURCES), PLAFONDS)).toEqual([]);
  });

  it("sets the general ceiling to 300 lines", () => {
    expect(PLAFOND_GENERAL).toBe(300);
  });

  it("lists only files above the general ceiling", () => {
    for (const plafond of Object.values(PLAFONDS)) {
      expect(plafond).toBeGreaterThan(PLAFOND_GENERAL);
    }
  });

  it("accepts a file outside the table at 300 lines", () => {
    expect(controler({ "a.ts": 300 }, {})).toEqual([]);
  });

  it("fails a file outside the table at 301 lines", () => {
    const messages = controler({ "pkg/a.ts": 301 }, {});
    expect(messages).toHaveLength(1);
    expect(messages[0]).toContain("pkg/a.ts");
    expect(messages[0]).toContain("301");
    expect(messages[0]).toContain("plafond 300");
    expect(messages[0]).toContain("Découpe le fichier plutôt que de relever le plafond");
  });

  it("fails a listed file above its ceiling", () => {
    const messages = controler({ "hooks/gros.ts": 401 }, { "hooks/gros.ts": 400 });
    expect(messages).toHaveLength(1);
    expect(messages[0]).toContain("401");
    expect(messages[0]).toContain("plafond 400");
    expect(messages[0]).toContain("plutôt que de relever le plafond");
  });

  it("accepts a listed file at its ceiling", () => {
    expect(controler({ "hooks/gros.ts": 400 }, { "hooks/gros.ts": 400 })).toEqual([]);
  });

  it("asks to lower the ceiling of a listed file that shrank", () => {
    const messages = controler({ "hooks/gros.ts": 350 }, { "hooks/gros.ts": 400 });
    expect(messages).toHaveLength(1);
    expect(messages[0]).toContain("350");
    expect(messages[0]).toContain("plafond 400");
    expect(messages[0]).toContain("baisse le plafond à 350");
  });

  it("asks to drop the entry of a listed file back under the general ceiling", () => {
    const messages = controler({ "hooks/gros.ts": 120 }, { "hooks/gros.ts": 400 });
    expect(messages).toHaveLength(1);
    expect(messages[0]).toContain("retire l'entrée de PLAFONDS");
  });

  it("fails a listed file that no longer exists", () => {
    const messages = controler({}, { "hooks/disparu.ts": 400 });
    expect(messages).toHaveLength(1);
    expect(messages[0]).toContain("hooks/disparu.ts");
    expect(messages[0]).toContain("Retire l'entrée");
  });
});

describe("mesurer", () => {
  function ecrire(racine: string, chemin: string, lignes: number, fin = "\n"): void {
    const cible = join(racine, chemin);
    mkdirSync(join(cible, ".."), { recursive: true });
    writeFileSync(cible, "const x = 1;\n".repeat(lignes - 1) + "const x = 1;" + fin);
  }

  function avecDossier(action: (racine: string) => void): void {
    const racine = mkdtempSync(join(tmpdir(), "longueur-"));
    try {
      action(racine);
    } finally {
      rmSync(racine, { recursive: true, force: true });
    }
  }

  it("counts .ts and .tsx files recursively with POSIX paths", () => {
    avecDossier((racine) => {
      ecrire(racine, "a.ts", 3);
      ecrire(racine, "pkg/b.tsx", 5);
      expect(mesurer(racine)).toEqual({ "a.ts": 3, "pkg/b.tsx": 5 });
    });
  });

  it("ignores test files and other extensions", () => {
    avecDossier((racine) => {
      ecrire(racine, "gros.test.ts", 500);
      ecrire(racine, "gros.test.tsx", 500);
      writeFileSync(join(racine, "style.css"), "a {}\n".repeat(500));
      expect(mesurer(racine)).toEqual({});
    });
  });

  it("counts the same with CRLF line endings and without a final newline", () => {
    avecDossier((racine) => {
      writeFileSync(join(racine, "crlf.ts"), "x;\r\n".repeat(4));
      ecrire(racine, "nu.ts", 4, "");
      expect(mesurer(racine)).toEqual({ "crlf.ts": 4, "nu.ts": 4 });
    });
  });

  it("makes a 301-line file outside the table fail end to end", () => {
    avecDossier((racine) => {
      ecrire(racine, "pkg/a.ts", 301);
      expect(controler(mesurer(racine), {})).toHaveLength(1);
    });
  });
});
