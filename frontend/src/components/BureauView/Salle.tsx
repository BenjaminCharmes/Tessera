import type { ReactNode } from "react";
import Agrandi from "../../design/bureau/Agrandi";
import { ECHELLE_DU_MOBILIER } from "../../lib/bureau/echelleDesSprites";
import NightVeil from "../../design/bureau/NightVeil";
import Plante from "../../design/bureau/Plante";
import Tuile from "../../design/bureau/Tuile";
import type { EspeceDePlante } from "../../design/bureau/Plante";
import { IconInfo } from "../../design/icons";
import { useLumiere } from "../../hooks/useLumiere";
import { cielDesFenetres } from "../../lib/bureau/ciel";
import { dayMoment } from "../../lib/bureau/dayMoment";
import MurLumineux from "./MurLumineux";

interface SalleProps {
  titre: string;
  /** Ce que la salle accueille : une phrase, en infobulle sur le titre (marque d'info), jamais écrite sous lui. */
  entete: string;
  /** Ce que dit la salle quand personne n'y est. */
  vide: string;
  /** Le mobilier : la salle elle-même, dessiné occupée ou non (ADR-058). */
  mobilier: ReactNode;
  /** Les autres meubles, posés au milieu du sol : jamais un état, toujours là (ADR-058). */
  decor?: ReactNode;
  /** Le mobilier porte un personnage (le bureau et sa figure assise) : il garde l'échelle des personnages. */
  personnageAuMobilier?: boolean;
  /** Un meuble à gauche du mobilier, qui se retrouve alors au milieu de la salle (ticket-727). */
  aGauche?: ReactNode;
  /** L'espèce de la plante du coin : chaque salle a la sienne. */
  plante?: EspeceDePlante;
  /** L'horloge unique de la vue : le ciel des fenêtres s'y lit (ticket-602). */
  maintenant: number;
  /** Le seul soleil du Bureau : la salle qui le porte le montre dans sa première fenêtre. */
  avecSoleil?: boolean;
  /** Ce qui s'accroche au mur à côté des fenêtres, quand une donnée le justifie. */
  accroche?: ReactNode;
  /** Contour ambre : quelqu'un ou quelque chose attend (une question, un repli). */
  ambre?: boolean;
  /** Une ligne par occupant, écrite dans l'en-tête ; sans ligne, la salle dit `vide` (ticket-637). */
  textes?: ReactNode[];
  /** Les personnages debout dans la salle, sans texte : le texte posé au sol était recouvert par le décor. */
  children?: ReactNode[];
}

/**
 * Le cadre commun des salles : un mur avec son titre fin, deux fenêtres, un plafonnier
 * et un interrupteur, puis la plinthe et le sol de 156 px, mobilier toujours là,
 * occupants à côté, une plante dans le coin. La nuit, un voile couvre la salle.
 */
export default function Salle({
  titre,
  entete,
  vide,
  mobilier,
  decor,
  aGauche,
  personnageAuMobilier = false,
  plante = "pot",
  maintenant,
  avecSoleil = false,
  accroche,
  ambre = false,
  textes = [],
  children = [],
}: SalleProps) {
  const occupee = textes.length > 0;
  const contour = ambre ? "border-amber-900" : "border-zinc-800";
  const moment = dayMoment(maintenant);
  const [lumiere, basculerLumiere] = useLumiere(`salle:${titre}`, moment);
  const ciels = cielDesFenetres(titre, 2, maintenant, avecSoleil);
  return (
    <aside
      aria-label={titre}
      data-occupee={occupee}
      data-moment={moment}
      data-contour={ambre ? "amber" : "neutre"}
      className={`relative flex min-w-0 flex-1 flex-col overflow-hidden rounded-lg border ${contour}`}
    >
      <Tuile motif="mur" moment={moment} />
      {/* L'en-tête de la salle, comme celui d'une pièce de projet : le plafond reste au plafonnier (ticket-727). */}
      <div
        data-entete="salle"
        className="relative flex items-center justify-between gap-2 border-b border-zinc-800 bg-zinc-900 px-3 py-[5px]"
      >
        <h3
          title={entete}
          className="flex shrink-0 items-center gap-1 whitespace-nowrap text-micro uppercase tracking-wide text-zinc-400"
        >
          {titre}
          <IconInfo size={12} data-marque="info" />
        </h3>
        {/* Ce que dit la salle vide, en face de son nom : le sol reste au mobilier. */}
        {occupee ? (
          <ul className="flex min-w-0 flex-1 flex-col gap-0.5 overflow-hidden text-right text-micro">
            {textes}
          </ul>
        ) : (
          <p className="min-w-0 flex-1 truncate text-right text-micro text-zinc-500">{vide}</p>
        )}
      </div>
      <div
        data-mur="salle"
        className="relative flex flex-nowrap items-start justify-center gap-1.5 overflow-hidden px-1.5 pt-3 pb-4 min-[1700px]:gap-3 min-[1700px]:px-3"
      >
        <MurLumineux
          moment={moment}
          ciels={ciels}
          allume={lumiere}
          onBasculer={basculerLumiere}
          maintenant={maintenant}
          salle={titre}
          plafonniers={1}
          accroche={accroche}
        />
      </div>
      <div className="relative h-[10.5px] shrink-0" data-plinthe="salle">
        <Tuile motif="plinthe" moment={moment} />
      </div>
      {/* Le fond du sol ne sert à rien dans une salle : le mobilier s'y centre au lieu de laisser un vide sous le mur (ticket-627). */}
      <div
        data-sol="lames"
        className="sol-lames relative flex flex-1 flex-col justify-center px-1"
      >
        <Tuile motif="sol" moment={moment} />
        {/* Regroupés au centre : répartis d'un bord à l'autre, ils laissaient de grands vides
            sur un écran large ou dézoomé (ticket-657). */}
        <div className="relative flex min-h-28 items-end justify-evenly gap-2 px-1 py-2">
          {aGauche && (
            <Agrandi relatif={ECHELLE_DU_MOBILIER}>
              <div className="flex shrink-0 items-end">{aGauche}</div>
            </Agrandi>
          )}
          <div className="flex min-w-0 items-center gap-4">
            <div className="shrink-0">
              <Agrandi relatif={personnageAuMobilier ? 1 : ECHELLE_DU_MOBILIER}>{mobilier}</Agrandi>
            </div>
            {children.length > 0 && (
              <ul className="flex min-w-0 items-end gap-3">{children}</ul>
            )}
          </div>
          {decor && (
            <Agrandi relatif={ECHELLE_DU_MOBILIER}>
              <div className="flex shrink-0 items-end gap-1">{decor}</div>
            </Agrandi>
          )}
          <Agrandi relatif={ECHELLE_DU_MOBILIER}>
            <Plante espece={plante} />
          </Agrandi>
        </div>
      </div>
      {moment === "nuit" && <NightVeil sombre={!lumiere} />}
    </aside>
  );
}
