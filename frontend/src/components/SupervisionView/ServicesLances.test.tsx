import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ServicesLances from "./ServicesLances";
import type { ServiceActif } from "../../types/api";

function service(over: Partial<ServiceActif> = {}): ServiceActif {
  return {
    nom: "frontend",
    project_id: "ide-core",
    pid: 1,
    demarre_a: new Date().toISOString(),
    en_cours: true,
    code_de_sortie: null,
    ...over,
  };
}

describe("ServicesLances", () => {
  it("rend cliquable l'adresse annoncee dans la sortie", () => {
    // Sans elle, on lance un serveur sans savoir ou il ecoute — le reproche
    // fait au bouton au premier usage.
    render(
      <ServicesLances
        services={[service()]}
        sortieDe={() => ["  ➜  Local:   http://localhost:5174/"]}
      />,
    );

    const lien = screen.getByRole("link", { name: /localhost:5174/ });
    expect(lien.getAttribute("href")).toBe("http://localhost:5174/");
  });

  it("n'affiche aucun lien quand la sortie n'en contient pas", () => {
    render(
      <ServicesLances services={[service()]} sortieDe={() => ["compilation"]} />,
    );

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("montre la sortie du service qu'on selectionne", () => {
    render(
      <ServicesLances
        services={[service()]}
        sortieDe={() => ["ligne une", "ligne deux"]}
      />,
    );

    expect(screen.queryByLabelText(/Sortie de/)).not.toBeInTheDocument();
    return userEvent
      .click(screen.getByRole("button", { name: "frontend" }))
      .then(() => {
        const sortie = screen.getByLabelText("Sortie de frontend");
        expect(sortie.textContent).toContain("ligne deux");
      });
  });

  it("montre un service mort avec son code, et sans adresse", () => {
    // Il a pu annoncer une adresse avant de mourir : la proposer enverrait
    // vers un serveur qui n'ecoute plus.
    render(
      <ServicesLances
        services={[
          service({ nom: "backend", en_cours: false, code_de_sortie: 1 }),
        ]}
        sortieDe={() => ["Uvicorn running on http://127.0.0.1:8000"]}
      />,
    );

    expect(screen.getByRole("button", { name: /code 1/ })).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("dit quand un service n'a rien ecrit, plutot qu'un cadre vide", async () => {
    render(<ServicesLances services={[service()]} sortieDe={() => []} />);

    await userEvent.click(screen.getByRole("button", { name: "frontend" }));

    expect(screen.getByLabelText("Sortie de frontend").textContent).toContain(
      "rien écrit",
    );
  });
});
