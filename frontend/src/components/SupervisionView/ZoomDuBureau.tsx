import { IconMinus, IconPlus } from "../../design/icons";
import Button from "../../design/ui/Button";
import { zoomVoisin } from "../../lib/bureau/zoomDuBureau";
import type { ModeDeZoom } from "../../lib/bureau/zoomDuBureau";

interface CommandesDeZoomProps {
  mode: ModeDeZoom;
  zoom: number;
  setMode: (mode: ModeDeZoom) => void;
  /** Le mode auquel « Ajuster » revient quand on le relâche (ticket-727). */
  defaut?: ModeDeZoom;
  /** Ce que le zoom agrandit : le Bureau, ou les salles des serveurs. */
  vue?: string;
}

/** − / pourcentage / + / Ajuster, dans l'en-tête de la Supervision ou d'« En cours ». */
export function CommandesDeZoom({ mode, zoom, setMode, defaut = 1, vue = "le Bureau" }: CommandesDeZoomProps) {
  const ajuste = mode === "ajuste";
  const nom = vue.replace(/^(le|les) /, "");
  return (
    <div
      role="group"
      aria-label={`Zoom ${vue === "le Bureau" ? "du Bureau" : `des ${nom}`}`}
      className="flex items-center gap-1"
    >
      <Button
        taille="compact"
        variante="discret"
        aria-label={`Dézoomer ${vue}`}
        onClick={() => setMode(zoomVoisin(zoom, -1))}
      >
        <IconMinus size={12} />
      </Button>
      <span className="w-10 text-center text-micro tabular-nums text-zinc-400">
        {Math.round(zoom * 100)} %
      </span>
      <Button
        taille="compact"
        variante="discret"
        aria-label={`Zoomer ${vue}`}
        onClick={() => setMode(zoomVoisin(zoom, 1))}
      >
        <IconPlus size={12} />
      </Button>
      <Button
        taille="compact"
        variante={ajuste ? "plein" : "discret"}
        aria-pressed={ajuste}
        title="Faire tenir toutes les pièces dans la hauteur de l'écran"
        onClick={() => setMode(ajuste ? defaut : "ajuste")}
      >
        Ajuster
      </Button>
    </div>
  );
}
