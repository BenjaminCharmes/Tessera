import type { ReactNode } from "react";
import Agrandi from "../../design/bureau/Agrandi";
import CeilingLamp from "../../design/bureau/CeilingLamp";
import NightVeil from "../../design/bureau/NightVeil";
import Plante from "../../design/bureau/Plante";
import type { EspeceDePlante } from "../../design/bureau/Plante";
import SkyWindow from "../../design/bureau/SkyWindow";
import { IconInfo } from "../../design/icons";
import { useLumiere } from "../../hooks/useLumiere";
import { cielDesFenetres } from "../../lib/bureau/ciel";
import { dayMoment } from "../../lib/bureau/dayMoment";
import BoutonLumiere from "./BoutonLumiere";

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
  const [gauche, droite] = cielDesFenetres(titre, 2, maintenant, avecSoleil);
  return (
    <aside
      aria-label={titre}
      data-occupee={occupee}
      data-contour={ambre ? "amber" : "neutre"}
      className={`relative flex min-w-0 flex-1 flex-col overflow-hidden rounded-lg border bg-(--sprite-mur) ${contour}`}
    >
      <div className="flex items-start justify-between gap-2 px-3 pt-[5px]">
        <h3
          title={entete}
          className="flex items-center gap-1 text-micro uppercase tracking-wide text-zinc-400"
        >
          {titre}
          <IconInfo size={12} data-marque="info" />
        </h3>
        {/* Ce que dit la salle vide, en face de son nom : le sol reste au mobilier. */}
        {occupee ? (
          <ul className="flex min-w-0 flex-col items-end gap-0.5 text-micro">
            {textes}
          </ul>
        ) : (
          <p className="truncate text-micro text-zinc-500">{vide}</p>
        )}
      </div>
      <div
        data-mur="salle"
        className="flex flex-nowrap items-start justify-center gap-1.5 overflow-hidden border-b-4 border-(--sprite-plinthe) px-1.5 pt-3 pb-4 min-[1700px]:gap-3 min-[1700px]:px-3"
      >
        <Agrandi>
          <SkyWindow
            moment={moment}
            soleil={gauche?.soleil}
            nuages={gauche?.nuages}
          />
        </Agrandi>
        <Agrandi>
          <CeilingLamp allume={lumiere} jour={moment !== "nuit"} />
        </Agrandi>
        <Agrandi>
          <SkyWindow
            moment={moment}
            soleil={droite?.soleil}
            nuages={droite?.nuages}
          />
        </Agrandi>
        {accroche}
        {/* Écarté de la fenêtre : collé à elle, il se lisait comme sa poignée (ticket-627). */}
        <span className="self-end min-[1700px]:ml-3">
          <BoutonLumiere
            salle={titre}
            allume={lumiere}
            onBasculer={basculerLumiere}
          />
        </span>
      </div>
      {/* Le fond du sol ne sert à rien dans une salle : le mobilier s'y centre au lieu de laisser un vide sous le mur (ticket-627). */}
      <div
        data-sol="lames"
        className="sol-lames flex flex-1 flex-col justify-center px-3"
      >
        {/* Regroupés au centre : répartis d'un bord à l'autre, ils laissaient de grands vides
            sur un écran large ou dézoomé (ticket-657). */}
        <div className="flex min-h-28 items-end justify-center gap-10 px-1 py-2">
          <div className="flex min-w-0 items-center gap-4">
            <div className="shrink-0">
              <Agrandi>{mobilier}</Agrandi>
            </div>
            {children.length > 0 && (
              <ul className="flex min-w-0 items-end gap-3">{children}</ul>
            )}
          </div>
          {decor && (
            <Agrandi>
              <div className="flex shrink-0 items-end gap-3">{decor}</div>
            </Agrandi>
          )}
          <Agrandi>
            <Plante espece={plante} />
          </Agrandi>
        </div>
      </div>
      {moment === "nuit" && <NightVeil sombre={!lumiere} />}
    </aside>
  );
}
