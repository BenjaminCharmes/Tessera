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
  alerte,
}: {
  nombre: number;
  alerte: AlerteDeSupervision;
}) {
  if (nombre === 0) return null;
  const couleur =
    alerte === "bloque"
      ? "bg-red-500/20 text-red-200"
      : alerte === "attente"
        ? "bg-amber-500/20 text-amber-200"
        : "bg-blue-500/20 text-blue-200";
  const titre =
    alerte === "bloque"
      ? `${nombre} run${nombre > 1 ? "s" : ""}, dont un bloqué`
      : alerte === "attente"
        ? `${nombre} run${nombre > 1 ? "s" : ""}, dont un attend une réponse`
        : `${nombre} run${nombre > 1 ? "s" : ""} en cours`;
  return (
    <span
      title={titre}
      aria-label={titre}
      className={`absolute right-0.5 top-0.5 min-w-4 rounded-full px-1 text-micro font-medium leading-4 ${couleur}`}
    >
      {nombre}
    </span>
  );
}
