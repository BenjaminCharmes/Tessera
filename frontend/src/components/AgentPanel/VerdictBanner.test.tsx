import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import VerdictBanner from "./VerdictBanner";

describe("VerdictBanner", () => {
  it("shows APPROVED banner for approved content", () => {
    render(<VerdictBanner content={"APPROVED\nLooks good, ship it!"} />);
    expect(screen.getByText(/APPROVED/)).toBeInTheDocument();
    expect(screen.getByText("Looks good, ship it!")).toBeInTheDocument();
  });

  it("shows CHANGES_REQUESTED banner when keyword is present", () => {
    render(
      <VerdictBanner content={"CHANGES_REQUESTED\nPlease fix the types."} />,
    );
    expect(screen.getByText(/CHANGES_REQUESTED/)).toBeInTheDocument();
    expect(screen.getByText("Please fix the types.")).toBeInTheDocument();
  });

  it("shows CHANGES_REQUESTED when both keywords appear (CHANGES_REQUESTED takes priority)", () => {
    render(
      <VerdictBanner content={"CHANGES_REQUESTED (not APPROVED)\nFix it."} />,
    );
    expect(screen.getByText(/CHANGES_REQUESTED/)).toBeInTheDocument();
  });

  it("shows CHANGES_REQUESTED when no keyword matches", () => {
    render(<VerdictBanner content={"The code needs work."} />);
    expect(screen.getByText(/CHANGES_REQUESTED/)).toBeInTheDocument();
  });

  it("renders without summary when content is only the keyword", () => {
    render(<VerdictBanner content={"APPROVED"} />);
    expect(screen.getByText(/APPROVED/)).toBeInTheDocument();
  });
});

describe("VerdictBanner — la revue complete", () => {
  const revue = [
    "CHANGES_REQUESTED",
    "J'ai lu le CONFIG réel et croisé avec la documentation. Voici ma review.",
    "",
    "1. La clé `tickMs` est absente du contrat export.",
    "2. Les fonctions ne sont pas sérialisables : il faut les écarter.",
  ].join("\n");

  it("montre le detail de la revue, pas seulement sa premiere ligne", async () => {
    // Panne d'usage : le bandeau ne gardait que `lines[0]`. Le reviewer
    // annoncait « Voici ma review » et l'utilisateur ne voyait rien de plus —
    // alors que le detail est la seule chose qui permette de juger.
    render(<VerdictBanner content={revue} />);

    await userEvent.click(screen.getByRole("button", { name: /détail/i }));

    expect(screen.getByText(/tickMs.*absente/)).toBeInTheDocument();
    expect(screen.getByText(/pas sérialisables/)).toBeInTheDocument();
  });

  it("ne propose pas de detail quand il n'y en a pas", () => {
    render(<VerdictBanner content={"APPROVED\nTout est bon."} />);

    expect(screen.queryByRole("button", { name: /détail/i })).toBeNull();
  });
});
