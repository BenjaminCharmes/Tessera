import type { EntreeHistorique } from "../../lib/historiqueNotifications";
import { TYPES_NOTIF } from "../../lib/notifications";
import { LIBELLES_TYPE } from "../../lib/reglagesNotifications";
import type { DonneesDeLaCloche } from "../../hooks/useNotificationsSysteme";

/** Les deux panneaux de la cloche — ticket-554. */
function heure(a: number): string {
  return new Date(a).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

interface AujourdhuiProps {
  historique: EntreeHistorique[];
  nonLus: number;
  onTout: () => void;
  onOuvrir: (projectId: string) => void;
}

export function PanneauAujourdhui({ historique, nonLus, onTout, onOuvrir }: AujourdhuiProps) {
  if (historique.length === 0) {
    return <p className="px-3 py-3 text-micro text-zinc-500">Rien depuis minuit.</p>;
  }
  return (
    <div>
      <div className="flex justify-end border-b border-zinc-800 px-3 py-1">
        <button
          type="button"
          disabled={nonLus === 0}
          onClick={onTout}
          className="text-micro text-zinc-400 hover:text-zinc-200 disabled:text-zinc-600"
        >
          Tout marquer comme lu
        </button>
      </div>
      <ul aria-label="Notifications du jour" className="max-h-80 overflow-y-auto">
        {historique.map((e) => (
          <li key={e.id}>
            <button
              type="button"
              onClick={() => onOuvrir(e.projectId)}
              className="flex w-full flex-col gap-0.5 px-3 py-2 text-left hover:bg-zinc-800/60"
            >
              <span className="flex justify-between gap-2 text-micro">
                <span className={e.lu ? "font-normal text-zinc-400" : "font-semibold text-zinc-100"}>
                  {e.titre}
                </span>
                <span className="shrink-0 text-zinc-500">{heure(e.a)}</span>
              </span>
              <span className="line-clamp-2 text-micro text-zinc-500">{e.corps}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function PanneauReglagesDesTypes({
  reglages,
  setReglage,
}: Pick<DonneesDeLaCloche, "reglages" | "setReglage">) {
  return (
    <table className="w-full text-micro">
      <thead>
        <tr className="text-zinc-500">
          <th scope="col" className="px-3 py-1 text-left font-normal">Événement</th>
          <th scope="col" className="px-2 py-1 font-normal">Système</th>
          <th scope="col" className="px-2 py-1 font-normal">Son</th>
        </tr>
      </thead>
      <tbody>
        {TYPES_NOTIF.map((type) => (
          <tr key={type} className="border-t border-zinc-800 text-zinc-300">
            <th scope="row" className="px-3 py-1.5 text-left font-normal">{LIBELLES_TYPE[type]}</th>
            {(["systeme", "son"] as const).map((champ) => (
              <td key={champ} className="px-2 py-1.5 text-center">
                <input
                  type="checkbox"
                  aria-label={`${LIBELLES_TYPE[type]} : ${champ === "systeme" ? "système" : "son"}`}
                  checked={reglages[type][champ]}
                  onChange={(e) => setReglage(type, champ, e.target.checked)}
                />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
