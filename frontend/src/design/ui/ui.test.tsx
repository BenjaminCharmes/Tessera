import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import StatusPill, { type EtatPastille } from "./StatusPill";
import Button from "./Button";
import ViewSwitcher from "./ViewSwitcher";
import { Chargement, Erreur, Vide } from "./ViewState";

describe("StatusPill", () => {
  const FAMILLES: [EtatPastille, string][] = [
    ["en-cours", "blue"],
    ["reussi", "green"],
    ["attention", "amber"],
    ["echec", "red"],
    ["neutre", "zinc"],
  ];

  it.each(FAMILLES)("renders the label and the %s colour family (%s)", (etat, famille) => {
    render(<StatusPill etat={etat} libelle="Mon état" />);

    const pastille = screen.getByText("Mon état");
    expect(pastille.className).toMatch(new RegExp(`(bg|text)-${famille}-\\d`));
  });
});

describe("Button", () => {
  it("carries a violet class in the plein variant", () => {
    render(<Button variante="plein">Lancer</Button>);

    expect(screen.getByRole("button", { name: "Lancer" }).className).toMatch(/violet-\d/);
  });

  it("never carries a solid red background in the arret variant", () => {
    render(<Button variante="arret">Arrêter</Button>);

    const classes = screen.getByRole("button", { name: "Arrêter" }).className;
    expect(classes).not.toMatch(/(^|\s)(hover:)?bg-red-/);
    expect(classes).toMatch(/border-red-/);
  });

  it("sizes 30 px by default and 26 px when compact", () => {
    render(
      <>
        <Button>Normal</Button>
        <Button taille="compact">Compact</Button>
      </>,
    );

    expect(screen.getByText("Normal").className).toContain("h-[30px]");
    expect(screen.getByText("Compact").className).toContain("h-[26px]");
  });
});

describe("ViewSwitcher", () => {
  const OPTIONS = [
    { valeur: "a", libelle: "Alpha" },
    { valeur: "b", libelle: "Beta" },
  ];

  it("marks the current option aria-pressed and calls onChange on click", async () => {
    const onChange = vi.fn();
    render(<ViewSwitcher options={OPTIONS} valeur="a" onChange={onChange} />);

    expect(screen.getByRole("button", { name: "Alpha" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Beta" })).toHaveAttribute("aria-pressed", "false");

    await userEvent.click(screen.getByRole("button", { name: "Beta" }));

    expect(onChange).toHaveBeenCalledWith("b");
  });
});

describe("ViewState", () => {
  it("Erreur shows its message and calls onRetry from « Réessayer »", async () => {
    const onRetry = vi.fn();
    render(<Erreur message="Panne" onRetry={onRetry} />);

    expect(screen.getByText("Panne")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));

    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("Vide shows its title, sentence and optional action", () => {
    render(<Vide titre="Rien ici" phrase="Lance un run." action={<button>Go</button>} />);

    expect(screen.getByText("Rien ici")).toBeInTheDocument();
    expect(screen.getByText("Lance un run.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go" })).toBeInTheDocument();
  });

  it("Chargement renders the requested number of skeleton lines", () => {
    render(<Chargement lignes={4} />);

    expect(screen.getByRole("status").children).toHaveLength(4);
  });
});
