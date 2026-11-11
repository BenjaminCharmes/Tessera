import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PuceFiltre from "./PuceFiltre";
import Compteur from "./Compteur";

describe("PuceFiltre", () => {
  it("exposes aria-pressed and the violet focus utility", () => {
    render(<PuceFiltre active={true} onClick={() => {}}>Tous</PuceFiltre>);
    const puce = screen.getByRole("button", { name: "Tous" });
    expect(puce).toHaveAttribute("aria-pressed", "true");
    expect(puce.className).toContain("focus-violet");
  });

  it("reports an inactive chip and fires onClick", () => {
    const onClick = vi.fn();
    render(<PuceFiltre active={false} onClick={onClick}>Échecs</PuceFiltre>);
    const puce = screen.getByRole("button", { name: "Échecs" });
    expect(puce).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(puce);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe("Compteur", () => {
  it("renders its count with the tone and placement classes", () => {
    render(<Compteur ton="red" position="absolute right-0">3</Compteur>);
    const c = screen.getByText("3");
    expect(c.className).toContain("bg-red-500/20");
    expect(c.className).toContain("absolute");
  });
});
