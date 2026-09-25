import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import AdresseDuService from "./AdresseDuService";

describe("AdresseDuService (ticket-173)", () => {
  it("ouvre l'adresse dans un nouvel onglet", () => {
    render(<AdresseDuService url="http://localhost:5174/" etiquette="Local" />);

    const lien = screen.getByRole("link");
    expect(lien.getAttribute("href")).toBe("http://localhost:5174/");
    expect(lien.getAttribute("target")).toBe("_blank");
    expect(lien.getAttribute("rel")).toContain("noreferrer");
  });

  it("montre l'étiquette quand il y en a une", () => {
    render(<AdresseDuService url="http://localhost:5174/" etiquette="Local" />);

    expect(screen.getByText("Local")).toBeInTheDocument();
  });

  it("se passe d'étiquette sans en inventer", () => {
    render(<AdresseDuService url="http://localhost:5174/" etiquette={null} />);

    expect(screen.getByRole("link").textContent).toBe("http://localhost:5174/");
  });

  it("se lit comme cliquable, pas comme une note de bas de page", () => {
    // Le rendu de la barre laterale etait souligne en pointilles ; celui-ci
    // est borde, comme en Supervision.
    render(<AdresseDuService url="http://localhost:5174/" etiquette={null} />);

    expect(screen.getByRole("link").className).toContain("border");
  });
});
