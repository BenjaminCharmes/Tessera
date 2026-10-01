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

  it("shows tooltip text with role tooltip on keyboard focus", () => {
    render(<InfoTip>Mon explication de test</InfoTip>);
    const button = screen.getByRole("button", { name: /plus d'informations/i });

    button.focus();

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

    // Focus opens the tooltip and gives the button keyboard events
    button.focus();
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
});
