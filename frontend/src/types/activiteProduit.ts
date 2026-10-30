/** Un agent qu'un produit déclare dans son fichier d'activité (ticket-671, ADR-064). */
export interface AgentDeProduit {
  id: string;
  nom: string;
  etat: "actif" | "repos";
  /** ISO 8601 ; `null` quand le produit ne le dit pas. */
  depuis: string | null;
  /** Un nom d'étape écrit par le produit : à rendre comme texte, jamais comme balisage. */
  libelle: string | null;
}

/** Les agents d'un service qui tourne ; vide quand le fichier est refusé (ticket-671). */
export interface ActiviteDeService {
  project_id: string;
  service: string;
  agents: AgentDeProduit[];
}
