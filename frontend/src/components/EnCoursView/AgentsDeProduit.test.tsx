import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import SallesDesServeurs from "./SallesDesServeurs";
import { api } from "../../lib/api";
import { lireActivite } from "../../lib/apiActivite";
import { _viderCacheResource } from "../../hooks/useResource";
import type { AppEnCours, ServiceActif } from "../../types/api";
import type { ActiviteDeService, AgentDeProduit } from "../../types/activiteProduit";

vi.mock("../../lib/apiActivite", () => ({ lireActivite: vi.fn() }));

const APP: AppEnCours = {
  project_id: "alpha",
  project_name: "Alpha",
  nom: "worker",
  origine: "tessera",
  pid: 100,
  ports: [8001],
  demarre_a: "2026-10-13T10:00:00Z",
  memoire_mo: 120.5,
};

function agent(over: Partial<AgentDeProduit>): AgentDeProduit {
  return { id: "triage", nom: "Triage", etat: "actif", depuis: null, libelle: null, ...over };
}

function activite(agents: AgentDeProduit[], over: Partial<ActiviteDeService> = {}): ActiviteDeService {
  return { project_id: "alpha", service: "worker", agents, ...over };
}

function rendre(reponse: ActiviteDeService[] | Error, apps: AppEnCours[] = [APP]) {
  const lire = vi.mocked(lireActivite);
  if (reponse instanceof Error) lire.mockRejectedValue(reponse);
  else lire.mockResolvedValue(reponse);
  render(<SallesDesServeurs apps={apps} lueA={0} enArret={() => false} onArreterProjet={vi.fn()} />);
  return lire;
}

function agentsDessines(): Element[] {
  return [...document.querySelectorAll("[data-sprite='agent-de-produit']")];
}

beforeEach(() => {
  _viderCacheResource();
  vi.spyOn(api.services, "list").mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("agents of a product", () => {
  it("draws one agent per entry, with its name and its label when it has one", async () => {
    rendre([
      activite([
        agent({ id: "triage", nom: "Triage des signaux", libelle: "lot 3 sur 5" }),
        agent({ id: "synthese", nom: "Synthèse", etat: "repos" }),
      ]),
    ]);

    await waitFor(() => expect(agentsDessines()).toHaveLength(2));
    const salle = screen.getByRole("article", { name: /Alpha/ });
    expect(within(salle).getByLabelText(/Triage des signaux, au travail/)).toBeInTheDocument();
    expect(within(salle).getByText("lot 3 sur 5")).toBeInTheDocument();
    expect(within(salle).getByLabelText(/Synthèse, au repos/)).toBeInTheDocument();
    expect(salle.querySelectorAll("[data-sprite='console']")).toHaveLength(2);
  });

  it("tells an active agent from a resting one, by pose and by motion", async () => {
    rendre([activite([agent({ id: "a", nom: "A", etat: "actif" }), agent({ id: "b", nom: "B", etat: "repos" })])]);

    await waitFor(() => expect(agentsDessines()).toHaveLength(2));
    const [actif, repos] = agentsDessines() as [Element, Element];
    expect(actif).toHaveAttribute("data-etat", "actif");
    expect(repos).toHaveAttribute("data-etat", "repos");
    expect(actif.querySelector("[data-bras='pupitre'].anim-tape")).not.toBeNull();
    expect(repos.querySelector("[data-bras='repos']")).not.toBeNull();
    expect(repos.querySelector("[class*='anim-']")).toBeNull();
    expect(screen.getByLabelText(/, A, au travail/)).toBeInTheDocument();
    expect(screen.getByLabelText(/, B, au repos/)).toBeInTheDocument();
    expect(actif.querySelector("[data-sprite='console'] .anim-defile")).not.toBeNull();
    expect(repos.querySelector("[data-sprite='console']")).toHaveAttribute("data-allume", "false");
  });

  it("draws no agent for an empty answer", async () => {
    const lire = rendre([]);

    await waitFor(() => expect(lire).toHaveBeenCalled());
    expect(agentsDessines()).toHaveLength(0);
    expect(document.querySelector("[data-agents-de-produit]")).toBeNull();
  });

  it("draws no agent when the request fails", async () => {
    const lire = rendre(new Error("hors ligne"));

    await waitFor(() => expect(lire).toHaveBeenCalled());
    expect(agentsDessines()).toHaveLength(0);
    expect(screen.getByRole("article", { name: /Alpha/ })).toBeInTheDocument();
  });

  it("draws no agent for an app whose service is absent from the answer", async () => {
    const lire = rendre([
      activite([agent({})], { service: "autre" }),
      activite([agent({})], { project_id: "beta" }),
    ]);

    await waitFor(() => expect(lire).toHaveBeenCalled());
    expect(agentsDessines()).toHaveLength(0);
  });

  it("puts each agent in the room of its own app", async () => {
    const autre: AppEnCours = { ...APP, pid: 200, project_id: "beta", project_name: "Beta", nom: "web" };
    rendre(
      [
        activite([agent({ id: "a", nom: "Agent alpha" })]),
        activite([agent({ id: "b", nom: "Agent beta" })], { project_id: "beta", service: "web" }),
      ],
      [APP, autre],
    );

    await waitFor(() => expect(agentsDessines()).toHaveLength(2));
    const alpha = screen.getByRole("article", { name: /Alpha/ });
    expect(within(alpha).getByLabelText(/Agent alpha/)).toBeInTheDocument();
    expect(within(alpha).queryByLabelText(/Agent beta/)).toBeNull();
  });

  it("renders a name and a label that contain markup as text", async () => {
    const piege = "<img src=x onerror=alert(1)><script>x</script>";
    rendre([activite([agent({ nom: "<b>Nom</b>", libelle: piege })])]);

    await waitFor(() => expect(agentsDessines()).toHaveLength(1));
    expect(screen.getByText(piege)).toBeInTheDocument();
    expect(screen.getByLabelText(/<b>Nom<\/b>/)).toBeInTheDocument();
    const liste = document.querySelector("[data-agents-de-produit]") as HTMLElement;
    expect(liste.querySelector("img, script, b")).toBeNull();
  });

  it("opens the journal of the agent's service when the agent is clicked", async () => {
    const service: ServiceActif = {
      nom: "worker", project_id: "alpha", pid: 100, demarre_a: "2026-10-13T10:00:00Z",
      en_cours: true, code_de_sortie: null, sortie: ["job 1 done"], arrete_a_la_main: false,
    };
    vi.mocked(api.services.list).mockResolvedValue([service]);
    rendre([activite([agent({ nom: "Triage" })])]);

    const bouton = await screen.findByRole("button", { name: /Triage, au travail/ });
    await waitFor(() => expect(document.querySelector("[data-ecran-mural='worker']")).not.toBeNull());
    fireEvent.click(bouton);
    expect(screen.getByRole("region", { name: /Journal de Alpha · worker/ })).toBeInTheDocument();
  });
});
