import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import MarkdownView from "./MarkdownView";

describe("MarkdownView", () => {
  it("rend les titres et l'emphase au lieu de leurs marqueurs", () => {
    render(<MarkdownView source={"# Titre\n\nUn **mot** fort."} />);

    expect(screen.getByRole("heading", { name: "Titre" })).toBeInTheDocument();
    expect(screen.getByText("mot").tagName).toBe("STRONG");
    expect(screen.queryByText(/##/)).toBeNull();
  });

  it("rend les listes et le code", () => {
    render(<MarkdownView source={"- un\n- deux\n\n`du code`"} />);

    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("du code").tagName).toBe("CODE");
  });

  it("n'execute pas le HTML trouve dans le document", () => {
    // Les tickets et la mémoire sont écrits par des agents. Rendre leur HTML
    // tel quel donnerait à un texte généré le pouvoir d'exécuter du script
    // dans une application qui a accès au système de fichiers (ticket-078).
    const { container } = render(
      <MarkdownView source={'<img src=x onerror="alert(1)">\n\n# Après'} />,
    );

    expect(container.querySelector("img[onerror]")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
    expect(screen.getByRole("heading", { name: "Après" })).toBeInTheDocument();
  });

  it("garde les liens mais leur retire les schemas actifs", () => {
    const { container } = render(
      <MarkdownView source={"[clic](javascript:alert(1))\n\n[ok](https://exemple.fr)"} />,
    );

    const href = container.querySelector('a[href^="javascript"]');
    expect(href).toBeNull();
    expect(container.querySelector('a[href="https://exemple.fr"]')).toBeTruthy();
  });
});
