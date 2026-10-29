import { useState } from "react";
import Fenetre from "../MiseEnLigne/Fenetre";
import Button from "../../design/ui/Button";
import { useCapturesDuRun } from "../../hooks/useCapturesDuRun";
import { grouperParEcran, urlDeCapture } from "../../lib/capturesDuRun";
import type { Capture } from "../../lib/capturesDuRun";

interface CapturesDuRunProps {
  projectId: string | null;
  ticketId: string;
}

function legende(capture: Capture): string {
  return `${capture.largeur} px · ${capture.theme}`;
}

/**
 * Les captures prises par l'étape de capture d'un run (ticket-620) : une vignette
 * par image, groupées par écran, qui s'ouvrent en grand. Rien n'est rendu quand
 * le run n'a rien capturé.
 */
export default function CapturesDuRun({ projectId, ticketId }: CapturesDuRunProps) {
  const fichiers = useCapturesDuRun(projectId, ticketId);
  const [ouverte, setOuverte] = useState<Capture | null>(null);
  const ecrans = grouperParEcran(fichiers);
  if (projectId === null || ecrans.length === 0) return null;
  const url = (c: Capture) => urlDeCapture(projectId, ticketId, c.fichier);

  return (
    <section aria-label="Captures" className="flex flex-col gap-2">
      <div className="text-mini font-semibold uppercase tracking-wider text-zinc-500">
        Captures
      </div>
      {ecrans.map(({ ecran, captures }) => (
        <div key={ecran}>
          <div className="mb-1 font-mono text-xs text-zinc-300">{ecran}</div>
          <ul className="flex flex-wrap gap-2">
            {captures.map((c) => (
              <li key={c.fichier}>
                <button
                  type="button"
                  onClick={() => setOuverte(c)}
                  aria-label={`${ecran} — ${legende(c)}`}
                  className="flex w-32 flex-col gap-1 rounded-sm border border-zinc-800 bg-zinc-900 p-1.5 text-left hover:border-zinc-600"
                >
                  <img src={url(c)} alt="" className="h-20 w-full rounded-sm object-cover object-top" />
                  <span className="text-mini text-zinc-400">{legende(c)}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
      {ouverte && (
        <Fenetre
          idTitre="capture-ouverte"
          bandeau="Capture"
          pied={<Button onClick={() => setOuverte(null)}>Fermer</Button>}
        >
          <p id="capture-ouverte" className="font-mono text-xs text-zinc-300">
            {ouverte.ecran} — {legende(ouverte)}
          </p>
          <img
            src={url(ouverte)}
            alt={`${ouverte.ecran}, ${legende(ouverte)}`}
            className="max-h-[60vh] w-full rounded-sm object-contain object-top"
          />
        </Fenetre>
      )}
    </section>
  );
}
