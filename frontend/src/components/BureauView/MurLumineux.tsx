import { Fragment } from "react";
import type { ReactNode } from "react";
import Agrandi from "../../design/bureau/Agrandi";
import CeilingLamp from "../../design/bureau/CeilingLamp";
import SkyWindow from "../../design/bureau/SkyWindow";
import type { CielDeFenetre } from "../../lib/bureau/ciel";
import type { DayMoment } from "../../lib/bureau/dayMoment";
import BoutonLumiere from "./BoutonLumiere";
import Pose from "./Pose";

/** Les abscisses (repère de 800 px) où le mur d'une pièce accroche ses éléments. */
export interface AbscissesDuMur {
  fenetres: readonly number[];
  plafonniers: readonly number[];
  interrupteur: number;
}

interface MurLumineuxProps {
  moment: DayMoment;
  /** Le ciel de chaque fenêtre, dans l'ordre : une fenêtre par entrée. */
  ciels: readonly CielDeFenetre[];
  allume: boolean;
  onBasculer: () => void;
  /** Le nom de la salle ou du projet, pour le nom accessible de l'interrupteur. */
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
 * Le mur lumineux d'une salle ou d'une pièce : fenêtres, plafonniers et interrupteur,
 * dessinés une seule fois pour les deux (ticket-631). Tout passe par `Agrandi`, interrupteur
 * compris : il suit l'échelle commune au lieu de garder ses pixels bruts.
 */
export default function MurLumineux({
  moment,
  ciels,
  allume,
  onBasculer,
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
      {/* Écarté de la fenêtre : collé à elle, il se lisait comme sa poignée (ticket-627). */}
      <span className="self-end min-[1700px]:ml-3">{bouton}</span>
    </>
  );
}
