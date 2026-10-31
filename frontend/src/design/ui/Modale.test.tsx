import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Modale from "./Modale";

describe("Modale", () => {
  it("renders its content in a modal dialog with the given label", () => {
    render(
      <Modale aria-label="Ma fenêtre">
        <p>Contenu</p>
      </Modale>,
    );

    const dialogue = screen.getByRole("dialog", { name: "Ma fenêtre" });
    expect(dialogue).toHaveAttribute("aria-modal", "true");
    expect(dialogue).toHaveTextContent("Contenu");
  });

  it("labels the dialog from an element when aria-labelledby is given", () => {
    render(
      <Modale aria-labelledby="titre">
        <h2 id="titre">Titre</h2>
      </Modale>,
    );

    expect(screen.getByRole("dialog", { name: "Titre" })).toBeInTheDocument();
  });

  it("closes on Escape", async () => {
    const onFermer = vi.fn();
    render(
      <Modale onFermer={onFermer} aria-label="m">
        <p>Contenu</p>
      </Modale>,
    );

    await userEvent.keyboard("{Escape}");

    expect(onFermer).toHaveBeenCalledTimes(1);
  });

  it("ignores the other keys", async () => {
    const onFermer = vi.fn();
    render(
      <Modale onFermer={onFermer} aria-label="m">
        <p>Contenu</p>
      </Modale>,
    );

    await userEvent.keyboard("a{Enter}");

    expect(onFermer).not.toHaveBeenCalled();
  });

  it("does not close on Escape while the closing is suspended", async () => {
    const onFermer = vi.fn();
    render(
      <Modale onFermer={onFermer} fermetureSuspendue aria-label="m">
        <p>Contenu</p>
      </Modale>,
    );

    await userEvent.keyboard("{Escape}");
    await userEvent.click(screen.getByRole("dialog"));

    expect(onFermer).not.toHaveBeenCalled();
  });

  it("closes on a click on the backdrop but not inside the content", async () => {
    const onFermer = vi.fn();
    render(
      <Modale onFermer={onFermer} aria-label="m">
        <p>Contenu</p>
      </Modale>,
    );

    await userEvent.click(screen.getByText("Contenu"));
    expect(onFermer).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("dialog"));
    expect(onFermer).toHaveBeenCalledTimes(1);
  });

  it("keeps the backdrop inert when fermerSurLeFond is off, Escape still closes", async () => {
    const onFermer = vi.fn();
    render(
      <Modale onFermer={onFermer} fermerSurLeFond={false} aria-label="m">
        <p>Contenu</p>
      </Modale>,
    );

    await userEvent.click(screen.getByRole("dialog"));
    expect(onFermer).not.toHaveBeenCalled();

    await userEvent.keyboard("{Escape}");
    expect(onFermer).toHaveBeenCalledTimes(1);
  });

  it("never closes by itself without onFermer", async () => {
    render(
      <Modale aria-label="m">
        <p>Contenu</p>
      </Modale>,
    );

    await userEvent.keyboard("{Escape}");
    await userEvent.click(screen.getByRole("dialog"));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("takes the focus on opening, unless the content already holds it", () => {
    const { unmount } = render(
      <Modale aria-label="m">
        <p>Contenu</p>
      </Modale>,
    );
    expect(screen.getByRole("dialog")).toHaveFocus();
    unmount();

    render(
      <Modale aria-label="m">
        <input aria-label="Champ" autoFocus />
      </Modale>,
    );
    expect(screen.getByRole("textbox", { name: "Champ" })).toHaveFocus();
  });

  it("stops clicks and keys from reaching a parent when isolated", () => {
    const surClic = vi.fn();
    const surTouche = vi.fn();
    render(
      <div onClick={surClic} onKeyDown={surTouche}>
        <Modale isoler aria-label="m">
          <button type="button">Dedans</button>
        </Modale>
      </div>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Dedans" }));
    fireEvent.keyDown(screen.getByRole("button", { name: "Dedans" }), { key: "Enter" });

    expect(surClic).not.toHaveBeenCalled();
    expect(surTouche).not.toHaveBeenCalled();
  });

  it("lets clicks and keys reach a parent when not isolated", () => {
    const surClic = vi.fn();
    render(
      <div onClick={surClic}>
        <Modale aria-label="m">
          <button type="button">Dedans</button>
        </Modale>
      </div>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Dedans" }));

    expect(surClic).toHaveBeenCalledTimes(1);
  });

  it("takes the backdrop tint it is given", () => {
    render(
      <Modale fond="bg-zinc-950/70" aria-label="m">
        <p>Contenu</p>
      </Modale>,
    );

    expect(screen.getByRole("dialog").className).toContain("bg-zinc-950/70");
  });
});
