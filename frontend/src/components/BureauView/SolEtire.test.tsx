import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
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
});
