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
  { id: "tests", label: "Tests" },
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
  reglages?: Partial<Pick<PipelineReglages, "securite_enabled" | "validateur_enabled" | "testeur_enabled">> | null,
): Set<string> {
  // Production et revue sont toujours actives.
  const actives = new Set<string>(["production", "revue"]);

  if (reglages !== undefined && reglages !== null) {
    if (reglages.testeur_enabled) actives.add("tests");
    if (reglages.securite_enabled) actives.add("securite");
    if (reglages.validateur_enabled) actives.add("validation");
    actives.add("documentation");
    actives.add("livraison");
  } else {
    // Fallback : déduire depuis les événements.
    if (events.some((e) => e.type === "test_result")) {
      actives.add("tests");
    }
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

/**
 * Détermine l'état d'une étape depuis l'instantané et les événements.
 *
 * `etapesEnCours` permet le suivi de plusieurs étapes actives en parallèle
 * (ticket-290 : reviewer + validateur simultanés). Quand cette liste est
 * fournie et non vide, elle prend le dessus sur le heuristique d'index.
 */
function etatEtape(
  id: string,
  etape: string | null,
  etapesEnCours: string[],
  events: OrchestratorEvent[],
): EtatEtape {
  // 1. Les événements de fin ont toujours priorité (ticket-279).
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
    case "tests":
      // Suite rouge → retour au codeur (rejected) ; suite verte → done (ticket-321).
      if (events.some((e) => e.type === "test_result" && e.data["passed"] === false))
        return "rejected";
      if (events.some((e) => e.type === "test_result" && e.data["passed"] === true))
        return "done";
      break;
    case "production":
      if (events.some((e) => e.type === "agent_done" && e.agent === "codeur")) return "done";
      break;
    case "revue":
      if (events.some((e) => e.type === "agent_done" && e.agent === "reviewer")) return "done";
      break;
  }

  // 2. Étape explicitement en cours (ticket-290 : parallélisme revue + validation).
  if (etapesEnCours.includes(id)) return "active";

  // 3. Heuristique d'index : uniquement quand aucune étape parallèle n'est connue,
  //    pour ne pas marquer "revue" comme done parce que "validation" a démarré
  //    alors qu'elles tournent en même temps.
  if (etapesEnCours.length === 0 && etape !== null) {
    const indexActuel = ORDRE_IDS.indexOf(etape);
    const indexEtape = ORDRE_IDS.indexOf(id);

    if (etape === id) return "active";

    if (indexActuel > indexEtape && indexActuel >= 0) {
      if (id === "securite" && events.some(
        (e) => e.type === "security_audit_done" && e.data["verdict"] === "BLOCK",
      )) return "rejected";
      if (id === "validation" && events.some(
        (e) => e.type === "validation_done" && estValidationRefusee(e),
      )) return "rejected";
      return "done";
    }
  }

  // 4. Détection active par événements (reconnexion sans etapesEnCours).
  switch (id) {
    case "production":
      if (events.some((e) => e.type === "agent_started" && e.agent === "codeur")) return "active";
      break;
    case "securite":
      if (events.some((e) => e.type === "security_audit_started")) return "active";
      break;
    case "revue":
      if (events.some((e) => e.type === "agent_started" && e.agent === "reviewer")) return "active";
      break;
    case "validation":
      if (events.some((e) => e.type === "validation_started")) return "active";
      break;
    case "documentation":
      if (events.some((e) => e.type === "documentation_started")) return "active";
      break;
    case "livraison":
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
  /** Étapes actives en parallèle (ticket-290). Vide par défaut. */
  etapesEnCours?: string[];
  /** Événements reçus pour enrichir ou suppléer l'état. */
  events: OrchestratorEvent[];
  /** Configuration du pipeline pour filtrer les étapes inactives. */
  reglages?: Partial<Pick<PipelineReglages, "securite_enabled" | "validateur_enabled" | "testeur_enabled">> | null;
}

/**
 * Frise d'étapes du pipeline, une pastille par étape active (ticket-256).
 *
 * L'état décide (depuis `etape` du snapshot), les événements enrichissent.
 * `etapesEnCours` permet d'afficher plusieurs pastilles actives en même temps
 * (ticket-290 : reviewer + validateur en parallèle).
 * Une étape que le projet désactive n'a pas de pastille.
 */
export default function StageStrip({ etape, etapesEnCours = [], events, reglages }: StageStripProps) {
  const actives = etapesActives(events, reglages);
  const visibles = ETAPES.filter((e) => actives.has(e.id));

  if (visibles.length === 0) return null;

  return (
    <div className="flex items-center px-3 pt-3 pb-2 gap-0">
      {visibles.map((stage, i) => (
        <Fragment key={stage.id}>
          <Pastille etat={etatEtape(stage.id, etape, etapesEnCours, events)} label={stage.label} />
          {i < visibles.length - 1 && (
            <div className="flex-1 h-px bg-zinc-700 mx-1 mb-4" />
          )}
        </Fragment>
      ))}
    </div>
  );
}
