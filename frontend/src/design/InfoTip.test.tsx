import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import InfoTip from "./InfoTip";

describe("InfoTip", () => {
  it("shows tooltip text with role tooltip on mouse hover", async () => {
    render(<InfoTip>Mon explication de test</InfoTip>);
    const button = screen.getByRole("button", { name: /plus d'informations/i });

    await userEvent.hover(button);

    expect(screen.getByRole("tooltip")).toHaveTextContent("Mon explication de test");
  });

  it("shows tooltip text with role tooltip on keyboard focus", async () => {
    render(<InfoTip>Mon explication de test</InfoTip>);
    const button = screen.getByRole("button", { name: /plus d'informations/i });

    await userEvent.tab();
    expect(button).toHaveFocus();

    expect(screen.getByRole("tooltip")).toHaveTextContent("Mon explication de test");
  });

  it("links the icon button to its text via aria-describedby", async () => {
    render(<InfoTip>Mon explication de test</InfoTip>);
    const button = screen.getByRole("button", { name: /plus d'informations/i });

    // Trigger hover so the tooltip is in the DOM
    await userEvent.hover(button);

    const tooltip = screen.getByRole("tooltip");
    const describedById = button.getAttribute("aria-describedby");
    expect(describedById).toBeTruthy();
    expect(tooltip).toHaveAttribute("id", describedById);
  });

  it("does not show tooltip text when not hovered or focused", () => {
    render(<InfoTip>Mon explication de test</InfoTip>);

    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("closes tooltip on Escape key", async () => {
    render(<InfoTip>Mon explication de test</InfoTip>);
    const button = screen.getByRole("button", { name: /plus d'informations/i });

    // Le focus clavier ouvre l'infobulle et donne les touches au bouton
    await userEvent.tab();
    expect(button).toHaveFocus();
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("hides tooltip again after mouse leaves", async () => {
    render(<InfoTip>Mon explication de test</InfoTip>);
    const button = screen.getByRole("button", { name: /plus d'informations/i });

    await userEvent.hover(button);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    await userEvent.unhover(button);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("rend la bulle dans un portal sur document.body et non dans le parent de l'icône", async () => {
    // La sidebar est overflow-hidden : un z-index seul ne dépasse pas ce
    // conteneur. Le portal rend la bulle directement dans document.body.
    render(<InfoTip>Mon explication de test</InfoTip>);
    const button = screen.getByRole("button", { name: /plus d'informations/i });

    await userEvent.hover(button);

    const tooltip = screen.getByRole("tooltip");
    expect(tooltip.parentElement).toBe(document.body);
  });
});
