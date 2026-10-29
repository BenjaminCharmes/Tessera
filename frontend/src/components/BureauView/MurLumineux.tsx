import { Fragment } from "react";
import type { ReactNode } from "react";
import Agrandi from "../../design/bureau/Agrandi";
import Cadre from "../../design/bureau/Cadre";
import CeilingLamp from "../../design/bureau/CeilingLamp";
import Horloge from "../../design/bureau/Horloge";
import SkyWindow from "../../design/bureau/SkyWindow";
import { imageDuCadre } from "../../lib/bureau/cadre";
import type { CielDeFenetre } from "../../lib/bureau/ciel";
import type { DayMoment } from "../../lib/bureau/dayMoment";
import BoutonLumiere from "./BoutonLumiere";
import Pose from "./Pose";

/** Les abscisses (repère de 800 px) où le mur d'une pièce accroche ses éléments. */
export interface AbscissesDuMur {
  fenetres: readonly number[];
  plafonniers: readonly number[];
  horloge: number;
  cadre: number;
  interrupteur: number;
}

interface MurLumineuxProps {
  moment: DayMoment;
  /** Le ciel de chaque fenêtre, dans l'ordre : une fenêtre par entrée. */
  ciels: readonly CielDeFenetre[];
  allume: boolean;
  onBasculer: () => void;
  /** L'horloge unique de la vue : les aiguilles de l'horloge murale s'y lisent (ticket-635). */
  maintenant: number;
  /** Le nom de la salle ou du projet : nom accessible de l'interrupteur, et graine du tableau du cadre. */
  salle: string;
  /** Combien de plafonniers, en flux ; avec `abscisses`, leur nombre est celui des abscisses. */
  plafonniers?: number;
  /** Sans abscisses, les éléments se suivent en flux ; avec, ils se posent contre le mur. */
  abscisses?: AbscissesDuMur;
  /** En flux seulement : ce qui s'accroche entre la dernière fenêtre et l'interrupteur. */
  accroche?: ReactNode;
}

interface ElementsProps {
  moment: DayMoment;
  ciels: readonly CielDeFenetre[];
  allume: boolean;
}

function Fenetre({ moment, ciel }: { moment: DayMoment; ciel?: CielDeFenetre }) {
  return (
    <Agrandi>
      <SkyWindow moment={moment} soleil={ciel?.soleil} nuages={ciel?.nuages ?? 0} />
    </Agrandi>
  );
}

function HorlogeMurale({ maintenant }: { maintenant: number }) {
  return (
    <Agrandi>
      <Horloge maintenant={maintenant} />
    </Agrandi>
  );
}

function Tableau({ salle }: { salle: string }) {
  return (
    <Agrandi>
      <Cadre image={imageDuCadre(salle)} />
    </Agrandi>
  );
}

function Plafonnier({ moment, allume }: { moment: DayMoment; allume: boolean }) {
  return (
    <Agrandi>
      <CeilingLamp allume={allume} jour={moment !== "nuit"} />
    </Agrandi>
  );
}

/** Le mur posé : chaque élément à son abscisse, les fenêtres au-dessous des plafonniers. */
function MurPose({ moment, ciels, allume, abscisses }: ElementsProps & { abscisses: AbscissesDuMur }) {
  return (
    <>
      {abscisses.fenetres.map((x, i) => (
        <Pose key={`fenetre-${x}`} x={x} bas="top-9">
          <Fenetre moment={moment} ciel={ciels[i]} />
        </Pose>
      ))}
      {abscisses.plafonniers.map((x) => (
        <Pose key={`plafonnier-${x}`} x={x} bas="top-0">
          <Plafonnier moment={moment} allume={allume} />
        </Pose>
      ))}
    </>
  );
}

/** Le mur en flux : fenêtre, plafonnier, fenêtre… un plafonnier après chaque fenêtre tant qu'il en reste. */
function MurEnFlux({ moment, ciels, allume, plafonniers }: ElementsProps & { plafonniers: number }) {
  return (
    <>
      {ciels.map((ciel, i) => (
        // L'ordre des fenêtres est fixe : l'indice est une clé stable.
        <Fragment key={`fenetre-${i}`}>
          <Fenetre moment={moment} ciel={ciel} />
          {i < plafonniers && <Plafonnier moment={moment} allume={allume} />}
        </Fragment>
      ))}
    </>
  );
}

/**
 * Le mur lumineux d'une salle ou d'une pièce : fenêtres, plafonniers, horloge, cadre et
 * interrupteur, dessinés une seule fois pour les deux (ticket-631, ticket-635). Tout passe par `Agrandi`, interrupteur
 * compris : il suit l'échelle commune au lieu de garder ses pixels bruts.
 */
export default function MurLumineux({
  moment,
  ciels,
  allume,
  onBasculer,
  maintenant,
  salle,
  plafonniers = 0,
  abscisses,
  accroche,
}: MurLumineuxProps) {
  const bouton = <BoutonLumiere salle={salle} allume={allume} onBasculer={onBasculer} />;
  if (abscisses) {
    return (
      <>
        <MurPose moment={moment} ciels={ciels} allume={allume} abscisses={abscisses} />
        <Pose x={abscisses.horloge} bas="top-5">
          <HorlogeMurale maintenant={maintenant} />
        </Pose>
        {/* Centré sur la hauteur des fenêtres (top-9) : plus haut qu'elles, il flottait. */}
        <Pose x={abscisses.cadre} bas="top-11">
          <Tableau salle={salle} />
        </Pose>
        <Pose x={abscisses.interrupteur} bas="bottom-10">
          {bouton}
        </Pose>
      </>
    );
  }
  return (
    <>
      <MurEnFlux moment={moment} ciels={ciels} allume={allume} plafonniers={plafonniers} />
      {accroche}
      <HorlogeMurale maintenant={maintenant} />
      {/* Ce qui s'accroche (le cadre de l'employé) prend la place du tableau : les deux
          ensemble faisaient déborder le bureau du directeur. Descendu au milieu de la
          hauteur des fenêtres, au lieu de s'aligner sur leur haut. */}
      {!accroche && (
        <span className="mt-1.5">
          <Tableau salle={salle} />
        </span>
      )}
      {/* Écarté de la fenêtre : collé à elle, il se lisait comme sa poignée (ticket-627). */}
      <span className="self-end min-[1700px]:ml-3">{bouton}</span>
    </>
  );
}
