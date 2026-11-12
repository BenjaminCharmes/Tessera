import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { jetonEnCache, oublierJeton } from "../../lib/auth";
import { send } from "../../lib/http";
import BandeauJeton, { CHEMIN_JETON_AUTRE, CHEMIN_JETON_WINDOWS } from "./index";

afterEach(() => {
  oublierJeton();
  vi.unstubAllGlobals();
});

async function provoquerUn401(): Promise<void> {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("non", { status: 401 })));
  await act(async () => {
    await send("/projects").catch(() => undefined);
  });
}

describe("BandeauJeton", () => {
  it("renders nothing until the backend answers 401", () => {
    render(<BandeauJeton />);

    expect(screen.queryByLabelText("Jeton de session")).toBeNull();
  });

  it("shows the field and the token file path after a 401", async () => {
    render(<BandeauJeton />);

    await provoquerUn401();

    expect(screen.getByLabelText("Jeton de session")).toBeTruthy();
    expect(screen.getByText(CHEMIN_JETON_WINDOWS)).toBeTruthy();
    expect(screen.getByText(CHEMIN_JETON_AUTRE)).toBeTruthy();
  });

  it("names STATIC_TOKEN and says the token lasts until the tab closes", async () => {
    render(<BandeauJeton />);

    await provoquerUn401();

    expect(screen.getByText("STATIC_TOKEN")).toBeTruthy();
    expect(screen.getByRole("alert").textContent).toContain(
      "Gardé jusqu'à la fermeture de l'onglet",
    );
  });

  it("hands the typed token to the session and hides itself", async () => {
    render(<BandeauJeton />);
    await provoquerUn401();

    await userEvent.type(screen.getByLabelText("Jeton de session"), "abc");
    await userEvent.click(screen.getByRole("button", { name: "Valider" }));

    expect(jetonEnCache()).toBe("abc");
    expect(screen.queryByLabelText("Jeton de session")).toBeNull();
  });
});
