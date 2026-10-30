import Confettis from "../../design/bureau/Confettis";
import IconeDuProjet from "../ProjetsView/IconeDuProjet";
import { useApercuDuProjet } from "../../hooks/useApercuDesProjets";
import type { MotifDeVisite } from "../../lib/bureau/ronde";
import Gyrophare from "../../design/bureau/Gyrophare";
import NightVeil from "../../design/bureau/NightVeil";
import Pastille from "../../design/bureau/Pastille";
import type { StreamState } from "../../hooks/streamState";
import { useActivites } from "../../hooks/useActivites";
import { useSonsDeLaPiece } from "../../hooks/useSonsDeLaPiece";
import { signauxSonores } from "../../lib/bureau/sons";
import {
  POSTE_DE_LA_LIVRAISON,
  machineEnService,
  placerLesAgents,
  postesFaits,
} from "../../lib/bureau/activites";
import type { Hasard } from "../../lib/bureau/activites";
import { bulleDOutil } from "../../lib/bureau/bulleDOutil";
import {
  copieVisible,
  libelleDeLaCopie,
  retourDeCopie,
} from "../../lib/bureau/copie";
import { dayMoment } from "../../lib/bureau/dayMoment";
import { ecranDuPoste } from "../../lib/bureau/ecranDuPoste";
import { contourDeLaPiece } from "../../lib/bureau/contourDeLaPiece";
import type { ContourDeLaPiece } from "../../lib/bureau/contourDeLaPiece";
import {
  contourEnCelebration,
  enFete,
  gyrophareAllume,
} from "../../lib/bureau/fete";
import StatusPill from "../../design/ui/StatusPill";
import { libelleDeSuite } from "../../lib/bureau/etapeDeSuite";
import { posteEnPlan } from "../../lib/bureau/plan";
import { postesDuRun } from "../../lib/bureau/postesDuRun";
import { placerLesRedacteurs } from "../../lib/bureau/redaction";
import { documentationEnCours, livraisonEnCours } from "../../lib/bureau/suite";
import { rolesDesPostes } from "../../lib/bureau/roleDuPoste";
import { postesAbsents } from "../../lib/bureau/sallesCommunes";
import type { PosteId } from "../../lib/bureau/postesDuRun";
import { enEtapeSilencieuse, santeAgent } from "../../lib/santeAgent";
import type { RunActif } from "../../types/api";
import ActionsDuRun from "./ActionsDuRun";
import AgentsDeLaPiece from "./AgentsDeLaPiece";
import FondDeLaPiece from "./FondDeLaPiece";
import PosteDeTravail from "./PosteDeTravail";
import SolEtire from "./SolEtire";
import { useLumiere } from "../../hooks/useLumiere";
import { useProjects } from "../../hooks/useProjects";
import { useServices } from "../../hooks/useServices";
import { ticketEnCours } from "../../lib/bureau/ticketEnCours";
import { servicesDeLaBaie } from "../../lib/bureau/servicesDeLaBaie";
import BoutonServices from "../Sidebar/BoutonServices";

interface PieceProps {
  projet: string;
  etat: StreamState;
  /** L'horloge unique de la vue : la pièce n'ouvre aucun minuteur. */
  maintenant: number;
  /** Le run vivant du projet : sans lui, pas de pile de dossiers. */
  runId?: string | null;
  /** Compteur d'événements de service, relu par la baie. */
  signalServices?: number;
  /** Le run du projet : sans lui, ni chrono ni accès au fil. */
  run?: RunActif;
  onOuvrir?: (runId: string) => void;
  onRanger?: (runId: string) => void;
  /** Choisit l'agent d'un poste occupé : le panneau « Agent choisi » le lit (ticket-582). */
  onChoisir?: (projet: string, poste: PosteId) => void;
  /** Choisit ce projet et ouvre l'onglet Tickets : la porte en est le raccourci (ticket-602). */
  onOpenProject?: (projet: string) => void;
  /** Le tirage des activités de pause : `Math.random` par défaut, une suite fixe dans les tests. */
  hasard?: Hasard;
  /** Le réglage « Son » du Bureau : coupé par défaut, la pièce ne joue rien (ticket-603). */
  sonActif?: boolean;
  /** Le poste derrière lequel le directeur se tient en visite dans cette pièce, ou rien (ticket-661). */
  directeur?: PosteId | null;
  /** Pourquoi il est venu, pour son infobulle (ticket-723). */
  motifDuDirecteur?: MotifDeVisite;
}

const CONTOURS: Record<ContourDeLaPiece, string> = {
  neutre: "border-zinc-800",
  vert: "border-green-900",
  rouge: "border-red-900",
  amber: "border-amber-900",
};

/** La pièce d'un projet : cinq postes dans l'ordre du pipeline, contour selon l'issue ou la santé. */
export default function Piece({
  projet,
  etat,
  maintenant,
  runId = null,
  signalServices = 0,
  run,
  onOuvrir,
  onRanger,
  onChoisir,
  onOpenProject,
  hasard,
  sonActif = false,
  directeur = null,
  motifDuDirecteur,
}: PieceProps) {
  const apercu = useApercuDuProjet(projet);
  const postes = postesDuRun(etat);
  const sante = santeAgent(
    etat.dernierEvenementA,
    maintenant,
    etat.pendingQuestion,
    etat.attenteExterieure !== null,
    enEtapeSilencieuse(etat),
  );
  // La PR mergée, ou la CI rouge : deux faits de la phase 2, lus dans les événements (ticket-598).
  const fete = enFete(etat, maintenant);
  const gyrophare = gyrophareAllume(etat);
  const contour = contourEnCelebration(
    contourDeLaPiece(etat, sante),
    fete,
    gyrophare,
  );
  const enCours = postes.some((p) => p.etat === "occupe");
  // Le dernier appel d'outil, dit en une ligne au-dessus du poste de l'agent (ticket-601).
  const outil = bulleDOutil(etat, maintenant);
  // Documentation et livraison n'ont pas de poste : la pastille du pied les dit (ticket-585).
  const suite = libelleDeSuite(etat.etape);
  // Aucun événement de ticket : pas de run, donc personne à dessiner.
  const auRepos = etat.ticketEvents.length === 0;
  // Run clos : les cinq agents sont partis par la porte. Sans run, personne à placer.
  const clos = !auRepos && etat.runClosed;
  const faits = auRepos ? [] : postesFaits(postes);
  const activites = useActivites(faits, maintenant, hasard);
  // Un agent chez le directeur ou aux RH n'est plus à sa place : il ne se dessine qu'à un endroit.
  const absents = postesAbsents(etat, maintenant);
  // Le refus du reviewer ou du validateur : il rapporte sa copie au codeur qui repart (ticket-599).
  const copie = copieVisible(retourDeCopie(etat, maintenant), {
    faits,
    absents,
    clos,
    fete,
  });
  // Le tour de plan : l'agent du poste se tient au tableau blanc, sa chaise est vide (ticket-623).
  const plan = posteEnPlan(etat);
  // La livraison dépose la PR à la boîte aux lettres ; la documentation, deux rédacteurs à la bibliothèque (ticket-624).
  const livraison = livraisonEnCours(etat) && !auRepos;
  const redacteurs = placerLesRedacteurs(documentationEnCours(etat) && !auRepos);
  const roles = rolesDesPostes(etat);
  const agents = placerLesAgents(
    faits,
    activites,
    clos,
    fete,
    copie?.poste ?? null,
    plan,
    livraison,
  ).map((a) =>
    absents.includes(a.poste) ? { ...a, activite: null, parti: true } : a,
  );
  // Fanfare, alarme, glouglou, frappes : ce que la pièce vient de montrer, dit à voix haute (ticket-603).
  useSonsDeLaPiece(signauxSonores(etat, fete, gyrophare, agents), sonActif);
  const moment = dayMoment(maintenant);
  const [lumiere, basculerLumiere] = useLumiere(projet, moment);
  // Une seule lecture des services : la baie au mur les montre, le bouton de l'en-tête les lance.
  const services = useServices(projet, signalServices);
  // ide-core fait tourner Tessera : ses serveurs tournent forcément, et « Lancer »
  // en démarrerait un second sur des ports déjà pris (ticket-152, ticket-632).
  const { projects } = useProjects();
  const faitTournerLIde = projects.find((p) => p.id === projet)?.fait_tourner_l_ide === true;
  const ticketCourant = ticketEnCours(etat, run);

  return (
    <section
      aria-label={projet}
      data-contour={contour}
      className={`overflow-hidden rounded-lg border bg-zinc-900 ${CONTOURS[contour]}`}
    >
      <div className="flex items-center justify-between gap-2 border-b border-zinc-800 px-3 py-[5px]">
        <div className="flex min-w-0 items-baseline gap-2">
          <IconeDuProjet projet={apercu ?? { id: projet, name: projet, icon: false }} taille="tuile" />
          <h3 className="shrink-0 text-corps font-semibold text-zinc-200">{projet}</h3>
          {/* Le ticket traité : la pile ne montre que les suivants (ticket-656). */}
          {ticketCourant && (
            <p
              data-testid="ticket-en-cours"
              title={ticketCourant.titre ? `${ticketCourant.id} — ${ticketCourant.titre}` : ticketCourant.id}
              className="truncate text-micro text-zinc-400"
            >
              <span className="font-mono text-zinc-300">{ticketCourant.id}</span>
              {ticketCourant.titre && ` — ${ticketCourant.titre}`}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Ce que la pièce dit d'elle-même : la fête, la copie rendue, la santé, ou l'étape sans poste. */}
          {fete && <StatusPill etat="reussi" libelle="PR mergée" />}
          {copie !== null && (
            <StatusPill etat="en-cours" libelle={libelleDeLaCopie(copie)} />
          )}
          {!fete && copie === null && enCours && <Pastille sante={sante} />}
          {!fete && !enCours && suite && (
            <StatusPill etat="en-cours" libelle={suite} />
          )}
          {!faitTournerLIde && (
            <BoutonServices
              services={services}
              libelleDuProjet={projet}
              enPastille
            />
          )}
          {run && (
            <ActionsDuRun
              run={run}
              etat={etat}
              onOuvrir={onOuvrir}
              onRanger={onRanger}
            />
          )}
        </div>
      </div>
      <div data-sol="lames" className="sol-lames relative">
        {/* Le repère de 800 px de la maquette, étiré sur la largeur de la pièce ; les sprites gardent leur taille. */}
        <SolEtire>
          <FondDeLaPiece
            projet={projet}
            etat={etat}
            machineEnService={machineEnService(agents)}
            maintenant={maintenant}
            allume={lumiere}
            onBasculerLumiere={basculerLumiere}
            runId={runId}
            services={servicesDeLaBaie(services, faitTournerLIde)}
            onOpenProject={onOpenProject && (() => onOpenProject(projet))}
          />
          <div className="grid h-40 grid-cols-5 items-end gap-1 border-b-8 border-transparent px-2.5">
            {postes.map((p) => (
              <PosteDeTravail
                key={p.poste}
                projet={projet}
                poste={p}
                role={roles[p.poste]}
                sante={sante}
                auRepos={auRepos}
                parti={clos || fete}
                absent={
                  absents.includes(p.poste) ||
                  plan === p.poste ||
                  (livraison && p.poste === POSTE_DE_LA_LIVRAISON)
                }
                onChoisir={onChoisir && ((poste) => onChoisir(projet, poste))}
                outil={outil?.poste === p.poste ? outil.phrase : null}
                ecran={ecranDuPoste(etat, p.poste, p.etat)}
              />
            ))}
          </div>
          <AgentsDeLaPiece projet={projet} agents={agents} roles={roles} redacteurs={redacteurs} directeur={directeur} motifDuDirecteur={motifDuDirecteur} />
          {fete && <Confettis />}
          {gyrophare && (
            <span className="absolute left-1/2 top-1 z-20 -translate-x-1/2">
              <Gyrophare />
            </span>
          )}
        </SolEtire>
        {moment === "nuit" && <NightVeil sombre={!lumiere} />}
      </div>
    </section>
  );
}
