import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FilDuRun from "./index";
import type { EntreeFil, EntreeTesteur } from "../../hooks/streamState";

function testeurEntry(over: Partial<EntreeTesteur> = {}): EntreeTesteur {
  return {
    genre: "testeur",
    id: "testeur-0",
    round: 1,
    passed: true,
    output_summary: "42 passed in 1.2s",
    errors: [],
    isDone: true,
    ...over,
  };
}

function agentEntry(over: Partial<Extract<EntreeFil, { genre: "agent" }>> = {}): Extract<EntreeFil, { genre: "agent" }> {
  return {
    genre: "agent",
    id: "codeur-0",
    agent: "codeur",
    round: 1,
    tokens: "",
    content: "",
    isDone: false,
    ...over,
  };
}

describe("FilDuRun — entrée sécurité (ticket-257)", () => {
  it("affiche le verdict d'un audit réussi", () => {
    const entries: EntreeFil[] = [
      {
        genre: "securite",
        id: "securite-0",
        round: 1,
        verdict: "APPROVED",
        summary: "Aucune faille détectée.",
        issues_count: 0,
        reason: "",
        isDone: true,
      },
    ];

    render(<FilDuRun entries={entries} />);

    expect(screen.getByText("SÉCURITÉ")).toBeInTheDocument();
    expect(screen.getByText("APPROVED")).toBeInTheDocument();
  });

  it("affiche le verdict BLOCK en rouge", () => {
    const entries: EntreeFil[] = [
      {
        genre: "securite",
        id: "securite-0",
        round: 1,
        verdict: "BLOCK",
        summary: "Faille critique détectée.",
        issues_count: 1,
        reason: "Injection SQL.",
        isDone: true,
      },
    ];

    render(<FilDuRun entries={entries} />);

    const verdict = screen.getByText("BLOCK");
    expect(verdict.closest(".text-red-400")).toBeTruthy();
  });
});

describe("FilDuRun — entrée validateur (ticket-257)", () => {
  it("affiche le verdict CHANGES_REQUESTED", () => {
    const entries: EntreeFil[] = [
      {
        genre: "validateur",
        id: "validateur-0",
        round: 1,
        verdict: "CHANGES_REQUESTED",
        feedback: "Deux critères échoués.",
        criteria: [
          { criterion: "Tests unitaires", passed: false, note: "Aucun test pour foo()." },
          { criterion: "Typage", passed: true, note: "" },
        ],
        isDone: true,
      },
    ];

    render(<FilDuRun entries={entries} />);

    expect(screen.getByText("VALIDATEUR")).toBeInTheDocument();
    expect(screen.getByText("CHANGES_REQUESTED")).toBeInTheDocument();
  });

  it("affiche la note d'un critere echoue quand l'entree validateur est depliee", async () => {
    // Scénario réel : après un refus du validateur, le codeur reprend (tour 2).
    // L'entrée validateur est donc non-dernière : elle est repliée par défaut.
    const entries: EntreeFil[] = [
      {
        genre: "validateur",
        id: "validateur-0",
        round: 1,
        verdict: "CHANGES_REQUESTED",
        feedback: "Deux critères échoués.",
        criteria: [
          { criterion: "Tests unitaires", passed: false, note: "Aucun test pour foo()." },
          { criterion: "Typage", passed: true, note: "" },
        ],
        isDone: true,
      },
      agentEntry({ id: "codeur-1", agent: "codeur", round: 2, isDone: false }),
    ];

    render(<FilDuRun entries={entries} />);

    // L'entrée est repliée : la note n'est pas dans le DOM.
    expect(screen.queryByText(/Aucun test pour foo/)).toBeNull();

    // Déplier l'entrée validateur.
    const header = screen.getByRole("button", { name: /VALIDATEUR/i });
    await userEvent.click(header);

    // La note du critère échoué est maintenant visible.
    expect(screen.getByText(/Aucun test pour foo/)).toBeInTheDocument();
  });

  it("affiche le feedback sous le verdict deplie", async () => {
    const entries: EntreeFil[] = [
      {
        genre: "validateur",
        id: "validateur-0",
        round: 1,
        verdict: "CHANGES_REQUESTED",
        feedback: "Deux critères échoués.",
        criteria: [],
        isDone: true,
      },
      agentEntry({ id: "codeur-1", agent: "codeur", round: 2, isDone: false }),
    ];

    render(<FilDuRun entries={entries} />);

    const header = screen.getByRole("button", { name: /VALIDATEUR/i });
    await userEvent.click(header);

    expect(screen.getByText("Deux critères échoués.")).toBeInTheDocument();
  });
});

describe("FilDuRun — en-têtes de verdict unifiés (ticket-282)", () => {
  it("reviewer approuvé, sécurité PASS et validateur APPROVED rendent la même icône de succès dans leur en-tête", () => {
    const entries: EntreeFil[] = [
      agentEntry({ id: "reviewer-0", agent: "reviewer", isDone: true, content: "APPROVED" }),
      {
        genre: "securite",
        id: "securite-1",
        round: 1,
        verdict: "PASS",
        summary: "",
        issues_count: 0,
        reason: "",
        isDone: true,
      },
      {
        genre: "validateur",
        id: "validateur-2",
        round: 1,
        verdict: "APPROVED",
        feedback: "",
        criteria: [],
        isDone: true,
      },
    ];

    render(<FilDuRun entries={entries} />);

    const blocs = screen.getAllByTestId("entree-pipeline");
    expect(blocs).toHaveLength(3);

    // Chaque en-tête doit porter la même icône SVG (IconCheck — la coche de succès).
    const iconPaths = blocs.map(
      (bloc) => bloc.querySelector("button svg path")?.getAttribute("d"),
    );
    expect(new Set(iconPaths).size).toBe(1);
    // La coche IconCheck contient "12.5" dans son tracé.
    expect(iconPaths[0]).toContain("12.5");
  });

  it("l'en-tête replié du codeur affiche sa durée et non la première ligne du rapport", () => {
    // Le codeur (tour 1) est terminé et non-dernier : son en-tête doit montrer
    // la durée, pas le début de son compte rendu.
    const entries: EntreeFil[] = [
      agentEntry({
        id: "codeur-0",
        agent: "codeur",
        round: 1,
        isDone: true,
        content: "python-multipart est absent des dépendances.",
        duration_ms: 170000,
      }),
      agentEntry({ id: "codeur-1", agent: "codeur", round: 2, isDone: false }),
    ];

    render(<FilDuRun entries={entries} />);

    const boutons = screen.getAllByRole("button");
    // Le premier bouton est l'en-tête du codeur du tour 1 (replié).
    const headerCodeur = boutons[0];

    expect(headerCodeur).toHaveTextContent("2 min 50 s");
    expect(headerCodeur).not.toHaveTextContent("python-multipart");
  });
});

describe("FilDuRun — carte TESTEUR (ticket-321)", () => {
  it("affiche une carte TESTEUR avec le résumé en en-tête sur une suite verte", () => {
    const entries: EntreeFil[] = [
      testeurEntry({ output_summary: "42 passed in 1.2s" }),
    ];

    render(<FilDuRun entries={entries} />);

    expect(screen.getByText("TESTEUR")).toBeInTheDocument();
    expect(screen.getByText("42 passed in 1.2s")).toBeInTheDocument();
  });

  it("affiche 'retour au codeur, sans revue' pour une suite rouge", () => {
    const entries: EntreeFil[] = [
      testeurEntry({
        passed: false,
        output_summary: "1 error in 2.32s",
        errors: ["FAILED test_foo.py::test_bar"],
      }),
    ];

    render(<FilDuRun entries={entries} />);

    expect(screen.getByText("retour au codeur, sans revue")).toBeInTheDocument();
  });

  it("affiche les erreurs dans le corps d'une carte TESTEUR rouge dépliée", async () => {
    // La carte rouge n'est pas la dernière : elle est repliée par défaut.
    const entries: EntreeFil[] = [
      testeurEntry({
        id: "testeur-0",
        passed: false,
        output_summary: "1 error in 2.32s",
        errors: ["FAILED test_foo.py::test_bar"],
      }),
      agentEntry({ id: "codeur-1", round: 2, isDone: false }),
    ];

    render(<FilDuRun entries={entries} />);

    // Erreur non visible tant que repliée.
    expect(screen.queryByText("FAILED test_foo.py::test_bar")).toBeNull();

    const header = screen.getByRole("button", { name: /TESTEUR/i });
    await userEvent.click(header);

    expect(screen.getByText("FAILED test_foo.py::test_bar")).toBeInTheDocument();
  });

  it("n'affiche pas les erreurs pour une carte TESTEUR verte", () => {
    const entries: EntreeFil[] = [
      testeurEntry({ passed: true, errors: [] }),
    ];

    render(<FilDuRun entries={entries} />);

    // Pas de liste d'erreurs pour une suite verte.
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("le verdict rouge de la carte TESTEUR utilise text-red (ADR-026)", () => {
    // ADR-026 : les états d'échec n'utilisent que la famille `red`.
    const entries: EntreeFil[] = [
      testeurEntry({ passed: false, output_summary: "1 error in 2.32s" }),
    ];

    render(<FilDuRun entries={entries} />);

    const verdictSpan = screen.getByText("retour au codeur, sans revue");
    expect(verdictSpan.closest(".text-red-400")).toBeTruthy();
  });

  it("les lignes d'erreur de la carte TESTEUR utilisent text-red (ADR-026)", async () => {
    // ADR-026 : les états d'échec n'utilisent que la famille `red`.
    // La carte est la dernière (seule) : elle est dépliée par défaut.
    const entries: EntreeFil[] = [
      testeurEntry({
        passed: false,
        output_summary: "1 error in 2.32s",
        errors: ["FAILED test_foo.py::test_bar"],
      }),
    ];

    render(<FilDuRun entries={entries} />);

    const ligne = screen.getByText("FAILED test_foo.py::test_bar");
    expect(ligne.className).toMatch(/text-red/);
  });
});

describe("FilDuRun — mélange d'entrées (ticket-257)", () => {
  it("rend toutes les entrées dans l'ordre", () => {
    const entries: EntreeFil[] = [
      agentEntry({ id: "codeur-0", agent: "codeur", round: 1, isDone: true, content: "ok" }),
      {
        genre: "securite",
        id: "securite-1",
        round: 1,
        verdict: "APPROVED",
        summary: "",
        issues_count: 0,
        reason: "",
        isDone: true,
      },
      agentEntry({ id: "reviewer-2", agent: "reviewer", round: 1, isDone: true, content: "APPROVED" }),
      {
        genre: "validateur",
        id: "validateur-3",
        round: 1,
        verdict: "APPROVED",
        feedback: "",
        criteria: [],
        isDone: true,
      },
    ];

    render(<FilDuRun entries={entries} />);

    const blocs = screen.getAllByTestId("entree-pipeline");
    expect(blocs).toHaveLength(4);
  });
});
