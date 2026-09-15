import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import QuotaBadge from "./QuotaBadge";

describe("QuotaBadge", () => {
  it("n'affiche rien tant que le quota est inconnu", () => {
    const { container } = render(<QuotaBadge quota={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("n'affiche rien quand le fournisseur n'a rien remonté", () => {
    // Un quota inconnu ne doit pas se déguiser en quota confortable.
    const { container } = render(<QuotaBadge quota={{ known: false }} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("affiche la proportion consommée", () => {
    render(
      <QuotaBadge
        quota={{ known: true, status: "allowed", utilization: 0.42 }}
      />,
    );
    expect(screen.getByText(/quota 42%/)).toBeInTheDocument();
  });

  it("signale l'interruption du run", () => {
    render(
      <QuotaBadge
        quota={{
          known: true,
          status: "allowed_warning",
          utilization: 0.95,
          run_interrupted: true,
        }}
      />,
    );
    expect(screen.getByText(/run interrompu/)).toBeInTheDocument();
  });

  it("dit explicitement qu'un quota rejeté est épuisé", () => {
    render(
      <QuotaBadge quota={{ known: true, status: "rejected", utilization: 1 }} />,
    );
    expect(screen.getByTitle(/épuisé/)).toBeInTheDocument();
  });
});
