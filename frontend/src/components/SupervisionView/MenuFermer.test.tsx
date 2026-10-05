import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import MenuFermer from "./MenuFermer";
import type { EntreeMenuFermer } from "./MenuFermer";

const ENTREES: EntreeMenuFermer[] = [
  { label: "Les terminés", issue: "termine", count: 2 },
  { label: "Les bloqués", issue: "bloque", count: 1 },
  { label: "En erreur", issue: "erreur", count: 0 },
  { label: "Tous les runs clos", issue: null, count: 3 },
];

describe("MenuFermer", () => {
  it("shows the number of closed runs on the trigger button", () => {
    render(<MenuFermer entrees={ENTREES} onFermer={vi.fn()} />);
    const bouton = screen.getByRole("button", { name: "Fermer par lot" });
    expect(bouton).toHaveTextContent("Fermer");
    expect(bouton).toHaveTextContent("3");
  });

  it("closes the menu on Escape", async () => {
    render(<MenuFermer entrees={ENTREES} onFermer={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Fermer par lot" }));
    expect(screen.getByRole("menu")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("closes the menu on a click outside", async () => {
    render(
      <div>
        <p>ailleurs</p>
        <MenuFermer entrees={ENTREES} onFermer={vi.fn()} />
      </div>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Fermer par lot" }));
    await userEvent.click(screen.getByText("ailleurs"));
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
