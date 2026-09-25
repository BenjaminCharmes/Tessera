import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import PanneauxDuProjet from "./PanneauxDuProjet";
import type { UseServicesResult } from "../../hooks/useServices";
import type { Project, ServiceActif } from "../../types/api";

function projet(over: Partial<Project> = {}): Project {
  return {
    id: "fluentdb",
    name: "FluentDB",
    path: "C:/p/fluentdb",
    description: "",
    active_agents: [],
    stack: null,
    raw_claude_md: "",
    github_remote: null,
    ...over,
  };
}

function service(over: Partial<ServiceActif> = {}): ServiceActif {
  return {
    nom: "dev",
    project_id: "fluentdb",
    pid: 4242,
    demarre_a: new Date().toISOString(),
    en_cours: true,
    code_de_sortie: null,
    ...over,
  };
}

function etat(over: Partial<UseServicesResult> = {}): UseServicesResult {
  return {
    services: [service()],
    enCours: true,
    enEchec: false,
    declare: true,
    erreur: null,
    demarrer: vi.fn(),
    arreter: vi.fn(),
    rafraichir: vi.fn(),
    ...over,
  };
}

function rendre(servicesOuverts: boolean, over: Partial<UseServicesResult> = {}) {
  return render(
    <PanneauxDuProjet
      project={projet()}
      gitOuvert={false}
      servicesOuverts={servicesOuverts}
      services={etat(over)}
      sortieDeService={() => []}
    />,
  );
}

describe("PanneauxDuProjet — ce qui rouvre le panneau (ticket-155)", () => {
  it("montre le panneau quand un service tourne, sans clic", () => {
    // Après Ctrl+R, `servicesOuverts` repart à false : le bouton disait
    // « Arrêter » et le panneau avait disparu. Le seul clic qui l'ouvrait
    // arrêtait aussi le service (ticket-155).
    rendre(false, { enCours: true });

    expect(screen.getByLabelText("Services du projet")).toBeInTheDocument();
  });

  it("ne le montre pas quand rien ne tourne et qu'on n'a pas cliqué", () => {
    rendre(false, { enCours: false, services: [] });

    expect(screen.queryByLabelText("Services du projet")).not.toBeInTheDocument();
  });

  it("le montre sur un clic, même si rien ne tourne encore", () => {
    // Le retour doit être immédiat : c'est le reproche du ticket-147.
    rendre(true, { enCours: false, services: [] });

    expect(screen.getByLabelText("Services du projet")).toBeInTheDocument();
  });

  it("le montre quand un service est mort de lui-même", () => {
    // C'est précisément le moment où l'on va chercher la sortie.
    rendre(false, {
      enCours: false,
      enEchec: true,
      services: [service({ en_cours: false, code_de_sortie: 1 })],
    });

    expect(screen.getByLabelText("Services du projet")).toBeInTheDocument();
  });
});

describe("PanneauxDuProjet — un projet qui ne declare rien (ticket-156)", () => {
  it("rend l'explication atteignable sans bouton de lancement", () => {
    // `RienDeclare` existait depuis ticket-147 sans que personne puisse
    // l'atteindre : le seul geste qui ouvrait le panneau etait le bouton de
    // lancement, et celui-ci ne s'affiche pas quand rien n'est declare.
    // Meme forme que ticket-152 pour le projet qui fait tourner l'IDE : une
    // absence de bouton s'explique en ouvrant le panneau d'office.
    rendre(false, { declare: false, services: [], enCours: false });

    expect(screen.getByLabelText("Services du projet")).toBeInTheDocument();
  });
});
