import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { EventType } from "../../types/api";
import {
  criteresDuCorps,
  criteresJuges,
  libelleDuTableau,
  ligneDeLInfobulle,
  tableauDesCriteres,
  ticketDuRun,
} from "./criteres";

function etatApres(evenements: { type: EventType; data?: Record<string, unknown> }[]): StreamState {
  return evenements.reduce<StreamState>(
    (s, e) =>
      applyEvent(s, {
        type: e.type,
        agent: null,
        ticket_id: "ticket-001",
        data: e.data ?? {},
        timestamp: "2026-10-27T10:00:00.000Z",
      }),
    INITIAL,
  );
}

const VERDICT = {
  criteria: [
    { criterion: "A", passed: true, note: "" },
    { criterion: "B", passed: false, note: "manque" },
  ],
};

describe("criteresDuCorps", () => {
  it("reads one criterion per checkbox line of the acceptance section", () => {
    const corps = [
      "## Objectif",
      "- [ ] pas un critère",
      "## Critères d'acceptation",
      "- [ ] Premier",
      "- [x] Deuxième",
      "texte libre",
      "## Ce que ça ne fait pas",
      "- [ ] hors section",
    ].join("\n");

    expect(criteresDuCorps(corps)).toEqual(["Premier", "Deuxième"]);
  });

  it("reads an English acceptance section with CRLF line ends", () => {
    expect(criteresDuCorps("## Acceptance criteria\r\n- [ ] One\r\n- [ ] Two\r\n")).toEqual(["One", "Two"]);
  });

  it("returns nothing when the section is absent or has no checkbox", () => {
    expect(criteresDuCorps("")).toEqual([]);
    expect(criteresDuCorps("## Critères d'acceptation\nrien à cocher")).toEqual([]);
  });
});

describe("ticketDuRun", () => {
  it("reads the ticket from the events of a single-ticket run", () => {
    expect(ticketDuRun(etatApres([{ type: "agent_started" }]))).toBe("ticket-001");
  });

  it("is null without any event or state", () => {
    expect(ticketDuRun(INITIAL)).toBeNull();
  });
});

describe("criteresJuges", () => {
  it("is null before any verdict", () => {
    expect(criteresJuges(INITIAL)).toBeNull();
  });

  it("reads the criteria of the last validation_done", () => {
    const etat = etatApres([
      { type: "validation_done", data: { criteria: [{ criterion: "Vieux", passed: false, note: "" }] } },
      { type: "validation_started" },
      { type: "validation_done", data: VERDICT },
    ]);

    expect(criteresJuges(etat)).toEqual([
      { criterion: "A", passed: true },
      { criterion: "B", passed: false },
    ]);
  });

  it("is null again once a new validation round has started", () => {
    const etat = etatApres([{ type: "validation_done", data: VERDICT }, { type: "validation_started" }]);

    expect(criteresJuges(etat)).toBeNull();
  });

  it("is null for a verdict that carries no criterion", () => {
    expect(criteresJuges(etatApres([{ type: "validation_done", data: { criteria: [] } }]))).toBeNull();
    expect(criteresJuges(etatApres([{ type: "validation_done", data: {} }]))).toBeNull();
  });
});

describe("tableauDesCriteres", () => {
  it("colours judged criteria and counts the passed ones", () => {
    const tableau = tableauDesCriteres(
      [
        { criterion: "A", passed: true },
        { criterion: "B", passed: false },
      ],
      ["ignoré"],
    );

    expect(tableau.lignes.map((l) => l.etat)).toEqual(["passe", "echoue"]);
    expect(tableau.valides).toBe(1);
  });

  it("draws one grey line per criterion of the ticket file while nothing is judged", () => {
    const tableau = tableauDesCriteres(null, ["A", "B", "C"]);

    expect(tableau.lignes.map((l) => l.etat)).toEqual(["attente", "attente", "attente"]);
    expect(tableau.valides).toBe(0);
  });

  it("stays empty when nothing is known", () => {
    expect(tableauDesCriteres(null, []).lignes).toEqual([]);
  });
});

describe("libelleDuTableau", () => {
  it("counts the validated criteria out of the total", () => {
    const tableau = { lignes: Array.from({ length: 5 }, () => ({ texte: "", etat: "passe" as const })), valides: 4 };

    expect(libelleDuTableau(tableau)).toBe("Tableau blanc : 4 critères sur 5 validés");
  });

  it("writes the singular for one validated criterion", () => {
    const lignes = [
      { texte: "", etat: "passe" as const },
      { texte: "", etat: "echoue" as const },
    ];

    expect(libelleDuTableau({ lignes, valides: 1 })).toBe("Tableau blanc : 1 critère sur 2 validés");
  });

  it("says no criterion is known on a blank board", () => {
    expect(libelleDuTableau({ lignes: [], valides: 0 })).toBe("Tableau blanc : aucun critère connu");
  });
});

describe("ligneDeLInfobulle", () => {
  it("writes the criterion and its state in full words", () => {
    expect(ligneDeLInfobulle({ texte: "Un test", etat: "passe" }, 0)).toBe("Un test — validé");
    expect(ligneDeLInfobulle({ texte: "Un test", etat: "echoue" }, 0)).toBe("Un test — refusé");
    expect(ligneDeLInfobulle({ texte: "Un test", etat: "attente" }, 0)).toBe("Un test — pas encore jugé");
  });

  it("numbers a criterion whose text is unknown", () => {
    expect(ligneDeLInfobulle({ texte: "", etat: "attente" }, 2)).toBe("Critère 3 — pas encore jugé");
  });
});
