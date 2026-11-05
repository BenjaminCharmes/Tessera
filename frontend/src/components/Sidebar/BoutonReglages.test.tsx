import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import BoutonReglages from "./BoutonReglages";

vi.mock("../../lib/apiReglages", async () => {
  const reel = await vi.importActual<typeof import("../../lib/apiReglages")>(
    "../../lib/apiReglages",
  );
  return {
    ...reel,
    reglages: { list: vi.fn().mockResolvedValue([]), ecrire: vi.fn(), retirer: vi.fn() },
  };
});

describe("BoutonReglages", () => {
  beforeEach(() => vi.clearAllMocks());

  it("opens_and_closes_the_panel", async () => {
    render(<BoutonReglages />);
    const bouton = screen.getByRole("button", { name: "Réglages" });
    expect(bouton).toHaveAttribute("aria-haspopup", "dialog");
    expect(screen.queryByRole("dialog")).toBeNull();
    await userEvent.click(bouton);
    expect(await screen.findByRole("dialog", { name: "Réglages globaux" })).toBeInTheDocument();
    await userEvent.click(bouton);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("closes_on_a_click_outside", async () => {
    render(
      <div>
        <BoutonReglages />
        <p>ailleurs</p>
      </div>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Réglages" }));
    await screen.findByRole("dialog");
    await userEvent.click(screen.getByText("ailleurs"));
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
