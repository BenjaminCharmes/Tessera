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

  it("draws the coffee machine, hidden from assistive tech, when empty", () => {
    const { container } = render(<SallePause occupants={[]} />);

    const machine = container.querySelector('[data-sprite="machine-a-cafe"]');
    expect(machine).not.toBeNull();
    expect(machine?.getAttribute("aria-hidden")).toBe("true");
    expect(screen.getByText("café")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Salle de pause" })).toHaveAttribute(
      "title",
      expect.stringMatching(/quota, CI, une dépendance/),
    );
    expect(screen.queryByText(/quota, CI, une dépendance/)).toBeNull();
  });

  it("keeps the coffee machine next to its occupants", () => {
    const { container } = render(
      <SallePause occupants={[{ projet: "alpha", pause: { motif: "ci", libelle: "CI en cours" } }]} />,
    );

    expect(container.querySelector('[data-sprite="machine-a-cafe"]')).not.toBeNull();
    expect(screen.getByText("alpha")).toBeInTheDocument();
    expect(screen.queryByText("Personne en pause")).toBeNull();
  });

  it("keeps its plant and its floor when nobody is in it", () => {
    render(<SallePause occupants={[]} />);

    const salle = screen.getByRole("complementary", { name: "Salle de pause" });
    expect(salle.querySelector('[data-sprite="plante"]')).not.toBeNull();
    expect(salle).toHaveAttribute("data-sol", "lames");
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

  it("draws the table, hidden from assistive tech, when empty", () => {
    const { container } = render(<SalleReunion occupants={[]} />);

    const table = container.querySelector('[data-sprite="table-de-reunion"]');
    expect(table).not.toBeNull();
    expect(table?.getAttribute("aria-hidden")).toBe("true");
    expect(screen.getByRole("heading", { name: "Salle de réunion" })).toHaveAttribute(
      "title",
      expect.stringMatching(/conflit de rebase/),
    );
    expect(screen.queryByText(/conflit de rebase/)).toBeNull();
  });

  it("places the resolver with the number of files of the conflict", () => {
    render(
      <SalleReunion occupants={[{ projet: "alpha", reunion: { temps: "conflit", fichiers: ["a.py", "b.py"] } }]} />,
    );

    const salle = screen.getByRole("complementary", { name: "Salle de réunion" });
    expect(within(salle).getByText(/résolveur/)).toBeInTheDocument();
    expect(within(salle).getByText(/2 fichiers/)).toBeInTheDocument();
  });

  it("says 'fichiers inconnus' when the conflict names none", () => {
    render(<SalleReunion occupants={[{ projet: "alpha", reunion: { temps: "conflit", fichiers: [] } }]} />);

    expect(screen.getByText(/fichiers inconnus/)).toBeInTheDocument();
  });

  it("keeps its plant and its floor when nobody is in it", () => {
    render(<SalleReunion occupants={[]} />);

    const salle = screen.getByRole("complementary", { name: "Salle de réunion" });
    expect(salle.querySelector('[data-sprite="plante"]')).not.toBeNull();
    expect(salle).toHaveAttribute("data-sol", "lames");
  });
});
