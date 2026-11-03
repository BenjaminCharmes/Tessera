import Agrandi from "../../design/bureau/Agrandi";
import BaieHaute from "../../design/bureau/BaieHaute";
import type { AppEnCours } from "../../types/api";
import AvecInfobulle from "../BureauView/AvecInfobulle";
import type { BaieDeSalle } from "./baies";
import { formaterHeure, formaterMo } from "./format";

interface BaieAvecFicheProps {
  baie: BaieDeSalle;
  /** Le processus de l'inventaire qui porte ce service ; absent, la fiche ne dit que l'état. */
  app: AppEnCours | undefined;
}

/**
 * Une baie et sa fiche, montrée au survol ou au focus clavier — ticket-710.
 * La fiche ne dit que ce que l'inventaire fournit (ADR-058). Seule la baie est
 * agrandie à l'échelle du mobilier. L'infobulle est celle des objets du Bureau.
 */
export default function BaieAvecFiche({ baie, app }: BaieAvecFicheProps) {
  return (
    <AvecInfobulle
      label={`${baie.nom} : ${baie.libelle}`}
      className="rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 hover:outline-2 hover:outline-offset-2 hover:outline-violet-500"
      infobulle={
        <>
          <p className="mb-1 font-semibold text-zinc-100">
            {baie.nom} · {baie.libelle}
          </p>
          {app ? (
            <dl className="grid grid-cols-[5rem_1fr] gap-x-2 font-mono text-mini leading-5">
              <dt className="text-zinc-500">pid</dt>
              <dd>{app.pid}</dd>
              <dt className="text-zinc-500">ports</dt>
              <dd>{app.ports.length ? app.ports.map((p) => `:${p}`).join(" ") : "—"}</dd>
              <dt className="text-zinc-500">mémoire</dt>
              <dd>{formaterMo(app.memoire_mo)}</dd>
              <dt className="text-zinc-500">démarré à</dt>
              <dd>{formaterHeure(app.demarre_a)}</dd>
              <dt className="text-zinc-500">origine</dt>
              <dd>{app.origine === "tessera" ? "lancé par Tessera" : "lancé à la main"}</dd>
            </dl>
          ) : (
            <p className="text-zinc-500">Aucun processus dans l&apos;inventaire.</p>
          )}
        </>
      }
    >
      <span data-baie={baie.nom} className="block">
        <Agrandi>
          <BaieHaute etat={baie.etat} />
        </Agrandi>
      </span>
    </AvecInfobulle>
  );
}
