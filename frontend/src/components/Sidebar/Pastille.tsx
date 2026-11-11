import Compteur, { type TonCompteur } from "../../design/ui/Compteur";
import type { AlerteDeSupervision } from "./panels";

/**
 * La pastille de la destination Supervision — ADR-026.
 *
 * Les cinq familles d'état et elles seules : `blue` pour l'activité, `amber`
 * pour une attente, `red` pour un blocage. Rien du tout quand rien ne tourne
 * — un badge à zéro occupe la place sans rien dire.
 */
export default function Pastille({
  nombre,
  alerte = null,
  unite = "run",
  titre: titreImpose,
}: {
  nombre: number;
  alerte?: AlerteDeSupervision;
  /** Ce que la pastille compte : « run » pour la supervision, « app » pour En cours. */
  unite?: string;
  /** Remplace le libellé par défaut (ex. un retard, qui n'est pas une question). */
  titre?: string;
}) {
  if (nombre === 0) return null;
  const ton: TonCompteur =
    alerte === "bloque"
      ? "red"
      : alerte === "attente"
        ? "amber"
        : "blue";
  const noms = `${nombre} ${unite}${nombre > 1 ? "s" : ""}`;
  const titreParDefaut =
    alerte === "bloque"
      ? `${noms}, dont un bloqué`
      : alerte === "attente"
        ? `${noms}, dont un attend une réponse`
        : `${noms} en cours`;
  const titre = titreImpose ?? titreParDefaut;
  return (
    <Compteur ton={ton} title={titre} aria-label={titre} position="absolute right-0.5 top-0.5">
      {nombre}
    </Compteur>
  );
}
