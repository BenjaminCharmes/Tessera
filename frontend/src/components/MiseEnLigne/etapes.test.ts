import { describe, expect, it } from "vitest";
import { estTerminee, fusionner, lireEvenement, nomDEtape } from "./etapes";
import { messageCourt } from "./useMiseEnLigne";
import type { EtapeMiseEnLigne } from "../../types/api";

function etape(step: string, state: EtapeMiseEnLigne["state"], detail = ""): EtapeMiseEnLigne {
  return { step, state, detail };
}

describe("lireEvenement", () => {
  const message = {
    type: "provisioning_step",
    project_id: "guessimo",
    data: { step: "dns", state: "manual", detail: "Pose les enregistrements." },
  };

  it("reads a well-formed event of the project", () => {
    expect(lireEvenement(message, "guessimo")).toEqual(
      etape("dns", "manual", "Pose les enregistrements."),
    );
  });

  it("ignores another project, another type and the snapshot", () => {
    expect(lireEvenement(message, "autre")).toBeNull();
    expect(lireEvenement({ ...message, type: "snapshot" }, "guessimo")).toBeNull();
  });

  it("ignores an unknown state or a malformed payload", () => {
    expect(lireEvenement({ ...message, data: { step: "dns", state: "weird" } }, "guessimo")).toBeNull();
    expect(lireEvenement({ ...message, data: { state: "done" } }, "guessimo")).toBeNull();
    expect(lireEvenement({ ...message, data: null }, "guessimo")).toBeNull();
  });

  it("defaults a missing detail to an empty string", () => {
    const sans = { ...message, data: { step: "dns", state: "done" } };
    expect(lireEvenement(sans, "guessimo")).toEqual(etape("dns", "done", ""));
  });
});

describe("fusionner", () => {
  it("starts every step of the plan as todo, in plan order", () => {
    expect(fusionner(["a", "b"], [], [])).toEqual([etape("a", "todo"), etape("b", "todo")]);
  });

  it("lets events win over the read, and the read over the plan", () => {
    const resultat = fusionner(
      ["a", "b", "c"],
      [etape("a", "skipped", "lu"), etape("b", "pending", "lu")],
      [etape("b", "done", "événement")],
    );

    expect(resultat).toEqual([
      etape("a", "skipped", "lu"),
      etape("b", "done", "événement"),
      etape("c", "todo"),
    ]);
  });

  it("appends a step unknown to the plan", () => {
    const resultat = fusionner(["a"], [], [etape("provisioning", "failed", "boom")]);

    expect(resultat.map((e) => e.step)).toEqual(["a", "provisioning"]);
  });
});

describe("estTerminee", () => {
  it("is false while some steps of the plan have not reported", () => {
    expect(estTerminee(["a", "b"], [etape("a", "done")])).toBe(false);
  });

  it("is true once every step of the plan has reported", () => {
    expect(estTerminee(["a", "b"], [etape("a", "done"), etape("b", "skipped")])).toBe(true);
  });

  it("is true on a failure or a step waiting for the user", () => {
    expect(estTerminee(["a", "b"], [etape("a", "failed")])).toBe(true);
    expect(estTerminee(["a", "b"], [etape("a", "needs_human")])).toBe(true);
  });

  it("is false for an empty plan with no event", () => {
    expect(estTerminee([], [])).toBe(false);
  });
});

describe("nomDEtape", () => {
  it("names known steps and falls back to the raw name", () => {
    expect(nomDEtape("vercel_project")).toBe("Projet Vercel");
    expect(nomDEtape("inconnue")).toBe("inconnue");
  });
});

describe("messageCourt", () => {
  it("reduces a 409 to one sentence without the body", () => {
    expect(messageCourt(new Error('API 409: {"detail":"lock held"}'))).toBe(
      "Une mise en ligne est déjà en cours pour ce projet.",
    );
  });

  it("keeps the reason of a 422", () => {
    expect(messageCourt(new Error('API 422: {"detail":"online block missing"}'))).toBe(
      "online block missing",
    );
  });

  it("falls back to a generic sentence on an unreadable body or another error", () => {
    const generique = "La mise en ligne n'a pas pu démarrer.";
    expect(messageCourt(new Error("API 422: not json"))).toBe(generique);
    expect(messageCourt(new Error("API 500: boom"))).toBe(generique);
    expect(messageCourt("oops")).toBe(generique);
  });
});
