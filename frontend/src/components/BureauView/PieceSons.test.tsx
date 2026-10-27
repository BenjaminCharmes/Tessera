import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import { api } from "../../lib/api";
import Piece from "./Piece";
import { DERNIER, T0, etatApresPhase2, etatEnCodage } from "./etatsDeTest";

const LIVRAISON = { type: "livraison_done", data: { pr_number: 42, arret: null } } as const;
const MERGEE = { type: "ci_merge_done", data: { merged: true } } as const;
const REFUSEE = { type: "ci_merge_done", data: { merged: false } } as const;

let oscillateursCrees = 0;

class FauxContexte {
  currentTime = 0;
  destination = {};
  close = vi.fn();
  createOscillator() {
    oscillateursCrees += 1;
    return { type: "sine", frequency: { value: 0 }, connect: vi.fn(), start: vi.fn(), stop: vi.fn(), onended: null };
  }
  createGain() {
    return {
      gain: { setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() },
      connect: vi.fn(),
    };
  }
}

beforeEach(() => {
  oscillateursCrees = 0;
  vi.useFakeTimers({ now: T0 });
  vi.stubGlobal("AudioContext", FauxContexte);
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function avancer(ms: number): void {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
}

function unDemarrage(etat: StreamState): StreamState {
  return applyEvent(etat, {
    type: "agent_started",
    agent: "reviewer",
    ticket_id: "ticket-001",
    data: {},
    timestamp: DERNIER,
  });
}

/** Monte la pièce à vide, laisse passer l'ouverture muette, puis donne l'état suivant. */
function monterPuisRecevoir(sonActif: boolean, suivant: StreamState, apresMs = 2_500) {
  const vue = render(<Piece projet="ide-core" etat={INITIAL} maintenant={T0 + 1_000} sonActif={sonActif} />);
  avancer(apresMs);
  vue.rerender(<Piece projet="ide-core" etat={suivant} maintenant={T0 + 1_000} sonActif={sonActif} />);
  return vue;
}

describe("Piece sounds", () => {
  it("creates no oscillator when the sound is off, whatever happens", () => {
    const vue = monterPuisRecevoir(false, etatApresPhase2([LIVRAISON, MERGEE]));
    vue.rerender(<Piece projet="ide-core" etat={etatApresPhase2([LIVRAISON, REFUSEE])} maintenant={T0} />);
    vue.rerender(<Piece projet="ide-core" etat={etatEnCodage()} maintenant={T0} />);

    expect(oscillateursCrees).toBe(0);
  });

  it("plays a three-note fanfare when the pull request is merged", () => {
    monterPuisRecevoir(true, etatApresPhase2([LIVRAISON, MERGEE]));

    expect(oscillateursCrees).toBe(3);
  });

  it("plays two low beeps when the CI turns red", () => {
    monterPuisRecevoir(true, etatApresPhase2([LIVRAISON, REFUSEE]));

    expect(oscillateursCrees).toBe(2);
  });

  it("plays three soft keystrokes when an agent starts working", () => {
    monterPuisRecevoir(true, etatEnCodage());

    expect(oscillateursCrees).toBe(3);
  });

  it("plays one sound only for two sound events less than a second apart", () => {
    const merge = etatApresPhase2([LIVRAISON, MERGEE]);
    const vue = monterPuisRecevoir(true, merge);
    avancer(500);

    vue.rerender(<Piece projet="ide-core" etat={unDemarrage(merge)} maintenant={T0 + 1_000} sonActif />);

    expect(oscillateursCrees).toBe(3);
  });

  it("plays the next sound once a second has passed", () => {
    const merge = etatApresPhase2([LIVRAISON, MERGEE]);
    const vue = monterPuisRecevoir(true, merge);
    avancer(1_000);

    vue.rerender(<Piece projet="ide-core" etat={unDemarrage(merge)} maintenant={T0 + 1_000} sonActif />);

    expect(oscillateursCrees).toBe(6);
  });

  it("plays nothing for events received during the first 2 seconds", () => {
    monterPuisRecevoir(true, etatApresPhase2([LIVRAISON, MERGEE]), 1_500);

    expect(oscillateursCrees).toBe(0);
  });

  it("does not play a merge that was already on screen when the view opened", () => {
    const merge = etatApresPhase2([LIVRAISON, MERGEE]);
    const vue = render(<Piece projet="ide-core" etat={merge} maintenant={T0 + 1_000} sonActif />);
    avancer(2_500);

    vue.rerender(<Piece projet="ide-core" etat={merge} maintenant={T0 + 1_000} sonActif />);

    expect(oscillateursCrees).toBe(0);
  });
});
