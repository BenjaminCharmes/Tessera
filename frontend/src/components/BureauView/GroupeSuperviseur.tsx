import { useState } from "react";
import Button from "../../design/ui/Button";
import type { CasSuperviseur } from "../../lib/bureau/aToi";
import RecapSuperviseur from "./RecapSuperviseur";

/**
 * Ce que le superviseur a laissé à relire, par projet, et la porte de son récap.
 * Lecture seule : aucun bouton n'accepte ni ne défait (ADR-080).
 */
export default function GroupeSuperviseur({ cas }: { cas: readonly CasSuperviseur[] }) {
  const [ouvert, setOuvert] = useState(false);

  return (
    <div className="flex flex-col gap-1.5">
      {cas.length > 0 && (
        <>
          <h4 className="text-micro uppercase tracking-wide text-zinc-500">Superviseur</h4>
          <ul className="flex flex-col gap-1.5">
            {cas.map(({ projet, ligne }) => (
              <li key={projet} className="flex flex-col text-xs text-zinc-300">
                <span>{projet}</span>
                <span className="text-micro text-amber-600">{ligne}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      {ouvert ? (
        <RecapSuperviseur onFermer={() => setOuvert(false)} />
      ) : (
        <Button taille="compact" onClick={() => setOuvert(true)}>
          Récap du superviseur
        </Button>
      )}
    </div>
  );
}
