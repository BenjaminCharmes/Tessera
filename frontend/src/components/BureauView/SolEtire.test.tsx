import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import { useMarcheActive } from "../../hooks/useEtirementDuSol";
import SolEtire from "./SolEtire";

function Temoin() {
  return (
    <span data-testid="temoin">
      {useMarcheActive() ? "marche" : "immobile"}
    </span>
  );
}

describe("SolEtire", () => {
  it("keeps agents from walking until the floor has been painted at its measured width", async () => {
    // Le 28/10, au retour sur la vue, tous les agents glissaient depuis la gauche (ticket-638).
    render(
      <SolEtire>
        <Temoin />
      </SolEtire>,
    );

    expect(screen.getByTestId("temoin")).toHaveTextContent("immobile");
    await waitFor(() =>
      expect(screen.getByTestId("temoin")).toHaveTextContent("marche"),
    );
  });

  it("stops the walk for one frame when the floor changes width, so agents jump instead of sliding", async () => {
    // Le 30/10, au retour sur le Bureau en mode « Ajuster », le zoom se mesurait
    // après le montage et les agents glissaient vers leur poste (ticket-720).
    let redimensionner: (largeur: number) => void = () => undefined;
    class FauxObservateur {
      constructor(rappel: ResizeObserverCallback) {
        redimensionner = (largeur) =>
          rappel([{ contentRect: { width: largeur } } as ResizeObserverEntry], this as unknown as ResizeObserver);
      }
      observe() {}
      disconnect() {}
    }
    vi.stubGlobal("ResizeObserver", FauxObservateur);
    render(
      <SolEtire>
        <Temoin />
      </SolEtire>,
    );
    await waitFor(() => expect(screen.getByTestId("temoin")).toHaveTextContent("marche"));

    act(() => redimensionner(1600));
    expect(screen.getByTestId("temoin")).toHaveTextContent("immobile");
    await waitFor(() => expect(screen.getByTestId("temoin")).toHaveTextContent("marche"));
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});
