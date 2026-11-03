import type { SignalementPayload, Ticket } from "../types/api";
import { agents, chat } from "./apiAgents";
import { git } from "./apiGit";
import { pipeline, projects, provisioning } from "./apiProjets";
import { orchestrator, runs, usage } from "./apiRuns";
import { services } from "./apiServices";
import { github, tickets } from "./apiTickets";
import { post } from "./apiVerbes";

/** Un seul objet pour les composants ; chaque domaine vit dans son module `api*.ts`. */
export const api = {
  projects,
  tickets,
  orchestrator,
  services,
  provisioning,
  runs,
  usage,
  github,
  pipeline,
  git,
  chat,
  agents,
};

/** Signale un défaut ou une idée sur Tessera : renvoie le ticket créé dans ide-core (ticket-408). */
export function signalerATessera(payload: SignalementPayload): Promise<Ticket> {
  return post<Ticket>("/signalements", payload);
}
