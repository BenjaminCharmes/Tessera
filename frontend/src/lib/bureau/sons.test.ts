import { describe, expect, it } from "vitest";
import { INITIAL } from "../../hooks/streamState";
import type { AgentPlace } from "./activites";
import { signauxSonores, sonsDeLaTransition } from "./sons";
import type { SignauxSonores } from "./sons";

const CALME: SignauxSonores = { fete: false, alarme: false, machine: 0, demarrages: 0 };

function agent(activite: AgentPlace["activite"], parti = false): AgentPlace {
  return { poste: "codeur", x: 0, niveau: "fond", activite, parti };
}

describe("sonsDeLaTransition", () => {
  it("makes no sound when nothing rises", () => {
    expect(sonsDeLaTransition(CALME, CALME)).toEqual([]);
  });

  it("maps each rising signal to its sound", () => {
    expect(sonsDeLaTransition(CALME, { ...CALME, fete: true })).toEqual(["fanfare"]);
    expect(sonsDeLaTransition(CALME, { ...CALME, alarme: true })).toEqual(["alarme"]);
    expect(sonsDeLaTransition(CALME, { ...CALME, machine: 1 })).toEqual(["glouglou"]);
    expect(sonsDeLaTransition(CALME, { ...CALME, demarrages: 1 })).toEqual(["frappes"]);
  });

  it("makes no sound when a signal falls", () => {
    const plein: SignauxSonores = { fete: true, alarme: true, machine: 2, demarrages: 3 };

    expect(sonsDeLaTransition(plein, CALME)).toEqual([]);
  });

  it("orders simultaneous sounds from the most to the least important", () => {
    const tout: SignauxSonores = { fete: true, alarme: true, machine: 1, demarrages: 1 };

    expect(sonsDeLaTransition(CALME, tout)).toEqual(["fanfare", "alarme", "glouglou", "frappes"]);
  });
});

describe("signauxSonores", () => {
  it("counts the agents at the machine and ignores those who left", () => {
    const agents = [agent("machine"), agent("machine", true), agent("tasse")];

    expect(signauxSonores(INITIAL, false, false, agents).machine).toBe(1);
  });

  it("carries the celebration and the alarm as they are", () => {
    const signaux = signauxSonores(INITIAL, true, false, []);

    expect(signaux).toEqual({ fete: true, alarme: false, machine: 0, demarrages: 0 });
  });
});
