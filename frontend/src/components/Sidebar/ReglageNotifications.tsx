import InfoTip from "../../design/InfoTip";
import type { EtatDesNotifications } from "../../hooks/useNotificationsSysteme";

/**
 * Couper ou rétablir les notifications système — ticket-192.
 *
 * « bloquées » et « coupées » ne se confondent pas : une permission refusée
 * une fois n'est plus redemandée par le navigateur, et le réglage seul n'y
 * changerait rien.
 *
 * L'explication de l'état « actives » passe en infobulle (ticket-273) :
 * c'est ce que font les notifications, pas un état à lire en permanence.
 * Les autres états restent affichés — « bloquées par le navigateur » demande
 * une action, la masquer ferait manquer l'information.
 */
const LIBELLES_ETAT: Partial<Record<EtatDesNotifications, string>> = {
  coupees: "coupées",
  bloquees: "bloquées par le navigateur : à autoriser dans ses réglages de site",
  indisponibles: "non prises en charge ici",
};

interface ReglageNotificationsProps {
  active: boolean;
  etat: EtatDesNotifications;
  onChange: (v: boolean) => void;
}

export default function ReglageNotifications({ active, etat, onChange }: ReglageNotificationsProps) {
  return (
    <label className="flex items-center gap-2 border-b border-zinc-800 px-3 py-1 text-micro text-zinc-400">
      <input
        type="checkbox"
        aria-label="Notifications système"
        checked={active}
        disabled={etat === "indisponibles"}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="text-zinc-300">Notifications</span>
      {etat === "actives" ? (
        <InfoTip>
          {"quand un agent pose une question, qu'un run se bloque ou finit"}
        </InfoTip>
      ) : (
        <span className="text-zinc-500">{LIBELLES_ETAT[etat]}</span>
      )}
    </label>
  );
}
