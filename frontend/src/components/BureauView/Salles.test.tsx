import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import SallePause from "./SallePause";
import SalleReunion from "./SalleReunion";

describe("SallePause", () => {
  it("shows the resume label of a run closed on an exhausted quota", () => {
    render(
      <SallePause
        occupants={[{ projet: "alpha", pause: { motif: "quota", libelle: "Quota épuisé, reprise 14:30 UTC" } }]}
      />,
    );

    const salle = screen.getByRole("complementary", { name: "Salle de pause" });
    expect(within(salle).getByText("alpha")).toBeInTheDocument();
    expect(within(salle).getByText(/reprise 14:30 UTC/)).toBeInTheDocument();
  });

  it("says the room is free without occupants", () => {
    render(<SallePause occupants={[]} />);

    expect(screen.getByText("Personne en pause")).toBeInTheDocument();
  });
});

describe("SalleReunion", () => {
  it("lists the conflict files, then the PR to read", () => {
    const { rerender } = render(
      <SalleReunion occupants={[{ projet: "alpha", reunion: { temps: "conflit", fichiers: ["a.py", "b.py"] } }]} />,
    );
    expect(screen.getByText(/a\.py, b\.py/)).toBeInTheDocument();

    rerender(<SalleReunion occupants={[{ projet: "alpha", reunion: { temps: "relecture", pr: 9 } }]} />);

    expect(screen.getByText("PR #9 à relire")).toBeInTheDocument();
    expect(screen.queryByText(/a\.py/)).toBeNull();
  });

  it("says the room is free without occupants", () => {
    render(<SalleReunion occupants={[]} />);

    expect(screen.getByText("Aucun conflit en cours")).toBeInTheDocument();
  });
});
