import { IconMinus, IconPlus } from "../../design/icons";
import Button from "../../design/ui/Button";
import { zoomVoisin } from "../../lib/bureau/zoomDuBureau";
import type { ModeDeZoom } from "../../lib/bureau/zoomDuBureau";

interface CommandesDeZoomProps {
  mode: ModeDeZoom;
  zoom: number;
  setMode: (mode: ModeDeZoom) => void;
}

/** − / pourcentage / + / Ajuster, dans l'en-tête de la Supervision. */
export function CommandesDeZoom({ mode, zoom, setMode }: CommandesDeZoomProps) {
  const ajuste = mode === "ajuste";
  return (
    <div
      role="group"
      aria-label="Zoom du Bureau"
      className="flex items-center gap-1"
    >
      <Button
        taille="compact"
        variante="discret"
        aria-label="Dézoomer le Bureau"
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
        aria-label="Zoomer le Bureau"
        onClick={() => setMode(zoomVoisin(zoom, 1))}
      >
        <IconPlus size={12} />
      </Button>
      <Button
        taille="compact"
        variante={ajuste ? "plein" : "discret"}
        aria-pressed={ajuste}
        title="Faire tenir toutes les pièces dans la hauteur de l'écran"
        onClick={() => setMode(ajuste ? 1 : "ajuste")}
      >
        Ajuster
      </Button>
    </div>
  );
}
