import { Fragment } from "react";
import { IconCheck, IconCross } from "../../design/icons";
import type { OrchestratorEvent, PipelineReglages } from "../../types/api";

/** État d'une étape dans la frise : faite, en cours, à venir ou refusée. */
type EtatEtape = "done" | "active" | "todo" | "rejected";

interface StageInfo {
  id: string;
  label: string;
}

/** Ordre canonique des étapes du pipeline. */
const ETAPES: StageInfo[] = [
  { id: "production", label: "Production" },
  { id: "securite", label: "Sécurité" },
  { id: "revue", label: "Revue" },
  { id: "validation", label: "Validation" },
  { id: "documentation", label: "Docs" },
  { id: "livraison", label: "Livraison" },
];

const ORDRE_IDS = ETAPES.map((e) => e.id);

/**
 * Vrai si un `validation_done` correspond à un refus.
 *
 * Depuis ticket-279 le backend émet `approved: boolean`. Les backends plus
 * anciens n'émettent que `verdict` — on retombe sur lui en dernier recours,
 * pour que la frise reste cohérente avec le Pipeline log (retour reviewer).
 */
function estValidationRefusee(e: OrchestratorEvent): boolean {
  if ("approved" in e.data) return e.data["approved"] === false;
  return typeof e.data["verdict"] === "string" && e.data["verdict"] !== "APPROVED";
}

/**
 * Détermine les étapes que ce projet active.
 *
 * Si `reglages` n'est pas fourni (observation sans contexte de projet),
 * on déduit les étapes présentes depuis les événements reçus.
 */
function etapesActives(
  events: OrchestratorEvent[],
  reglages?: Pick<PipelineReglages, "securite_enabled" | "validateur_enabled"> | null,
): Set<string> {
  // Production et revue sont toujours actives.
  const actives = new Set<string>(["production", "revue"]);

  if (reglages !== undefined && reglages !== null) {
    if (reglages.securite_enabled) actives.add("securite");
    if (reglages.validateur_enabled) actives.add("validation");
    actives.add("documentation");
    actives.add("livraison");
  } else {
    // Fallback : déduire depuis les événements.
    if (events.some((e) => e.type === "security_audit_started" || e.type === "security_audit_done")) {
      actives.add("securite");
    }
    if (events.some((e) => e.type === "validation_started" || e.type === "validation_done")) {
      actives.add("validation");
    }
    if (events.some((e) => e.type === "documentation_started" || e.type === "doc_updated")) {
      actives.add("documentation");
    }
    if (events.some((e) => e.type === "livraison_started" || e.type === "livraison_done")) {
      actives.add("livraison");
    }
  }

  return actives;
}

/** Détermine l'état d'une étape depuis l'instantané et les événements. */
function etatEtape(
  id: string,
  etape: string | null,
  events: OrchestratorEvent[],
): EtatEtape {
  // L'instantané décide : si l'étape actuelle est plus avancée, celle-ci est done.
  const indexActuel = etape ? ORDRE_IDS.indexOf(etape) : -1;
  const indexEtape = ORDRE_IDS.indexOf(id);

  if (etape === id) {
    // Une étape peut recevoir son événement de fin pendant qu'elle est encore
    // active dans l'instantané (livraison_done reçu avant run_closed, par ex.).
    // On vérifie d'abord les événements de fin avant de rendre "active" (ticket-279).
    switch (id) {
      case "livraison":
        if (events.some((e) => e.type === "livraison_done")) return "done";
        break;
      case "documentation":
        if (events.some((e) => e.type === "doc_updated" || e.type === "documentation_failed"))
          return "done";
        break;
      case "validation":
        if (events.some((e) => e.type === "validation_done" && estValidationRefusee(e)))
          return "rejected";
        if (events.some((e) => e.type === "validation_done")) return "done";
        break;
      case "securite":
        if (events.some((e) => e.type === "security_audit_done" && e.data["verdict"] === "BLOCK"))
          return "rejected";
        if (events.some((e) => e.type === "security_audit_done")) return "done";
        break;
    }
    return "active";
  }

  if (indexActuel > indexEtape && indexActuel >= 0) {
    // On est plus loin dans le pipeline — mais cette étape a-t-elle été refusée ?
    if (id === "securite" && events.some(
      (e) => e.type === "security_audit_done" && e.data["verdict"] === "BLOCK",
    )) {
      return "rejected";
    }
    if (id === "validation" && events.some(
      (e) => e.type === "validation_done" && estValidationRefusee(e),
    )) {
      return "rejected";
    }
    return "done";
  }

  // Pas de contexte depuis l'instantané : se fier aux événements.
  switch (id) {
    case "production":
      if (events.some((e) => e.type === "agent_done" && e.agent === "codeur")) return "done";
      if (events.some((e) => e.type === "agent_started" && e.agent === "codeur")) return "active";
      break;
    case "securite": {
      const auditsDone = events.filter((e) => e.type === "security_audit_done");
      if (auditsDone.some((e) => e.data["verdict"] === "BLOCK")) return "rejected";
      if (auditsDone.length > 0) return "done";
      if (events.some((e) => e.type === "security_audit_started")) return "active";
      break;
    }
    case "revue":
      if (events.some((e) => e.type === "agent_done" && e.agent === "reviewer")) return "done";
      if (events.some((e) => e.type === "agent_started" && e.agent === "reviewer")) return "active";
      break;
    case "validation": {
      const validsDone = events.filter((e) => e.type === "validation_done");
      if (validsDone.some(estValidationRefusee)) return "rejected";
      if (validsDone.length > 0) return "done";
      if (events.some((e) => e.type === "validation_started")) return "active";
      break;
    }
    case "documentation":
      if (events.some((e) => e.type === "doc_updated")) return "done";
      if (events.some((e) => e.type === "documentation_started")) return "active";
      break;
    case "livraison":
      if (events.some((e) => e.type === "livraison_done")) return "done";
      if (events.some((e) => e.type === "livraison_started")) return "active";
      break;
  }

  return "todo";
}

interface PastilleProps {
  etat: EtatEtape;
  label: string;
}

/** Une pastille colorée avec son étiquette, aux couleurs ADR-026. */
function Pastille({ etat, label }: PastilleProps) {
  const ring: Record<EtatEtape, string> = {
    done: "bg-green-600 text-green-100",
    active: "bg-blue-500 text-blue-100 animate-pulse",
    todo: "bg-zinc-700 text-zinc-500",
    rejected: "bg-red-600 text-red-100",
  };

  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={`w-5 h-5 rounded-full flex items-center justify-center ${ring[etat]}`}
        aria-label={`${label} : ${etat}`}
      >
        {etat === "done" && <IconCheck size={10} />}
        {etat === "rejected" && <IconCross size={10} />}
      </div>
      <span className="text-micro text-zinc-500 leading-none">{label}</span>
    </div>
  );
}

interface StageStripProps {
  /** Étape en cours depuis le snapshot du run (ticket-255). */
  etape: string | null;
  /** Événements reçus pour enrichir ou suppléer l'état. */
  events: OrchestratorEvent[];
  /** Configuration du pipeline pour filtrer les étapes inactives. */
  reglages?: Pick<PipelineReglages, "securite_enabled" | "validateur_enabled"> | null;
}

/**
 * Frise d'étapes du pipeline, une pastille par étape active (ticket-256).
 *
 * L'état décide (depuis `etape` du snapshot), les événements enrichissent.
 * Une étape que le projet désactive n'a pas de pastille.
 */
export default function StageStrip({ etape, events, reglages }: StageStripProps) {
  const actives = etapesActives(events, reglages);
  const visibles = ETAPES.filter((e) => actives.has(e.id));

  if (visibles.length === 0) return null;

  return (
    <div className="flex items-center px-3 pt-3 pb-2 gap-0">
      {visibles.map((stage, i) => (
        <Fragment key={stage.id}>
          <Pastille etat={etatEtape(stage.id, etape, events)} label={stage.label} />
          {i < visibles.length - 1 && (
            <div className="flex-1 h-px bg-zinc-700 mx-1 mb-4" />
          )}
        </Fragment>
      ))}
    </div>
  );
}
