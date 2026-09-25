import type { AdresseAnnoncee } from "./adresse";

/**
 * L'adresse d'un service, rendue au même endroit qu'ailleurs — ticket-173.
 *
 * Le même lien se dessinait de deux façons : souligné en pointillés dans la
 * barre latérale, en pastille bordée dans la Supervision. Deux
 * implémentations, écrites à deux moments — la dérive qu'ADR-034 vise.
 *
 * La pastille l'emporte : bordée, elle se lit comme quelque chose qu'on peut
 * cliquer, là où un soulignement pointillé se lit comme une note de bas de
 * page. ADR-026 : `zinc` au repos, aucune couleur d'état — une adresse n'en
 * est pas un.
 */
export default function AdresseDuService({ url, etiquette }: AdresseAnnoncee) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      title={etiquette ? `${etiquette} · ${url}` : url}
      className="inline-flex max-w-full items-center gap-1.5 rounded-sm border border-zinc-700 px-1.5 py-0.5 text-micro text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200"
    >
      {etiquette ? (
        <span className="shrink-0 text-zinc-500">{etiquette}</span>
      ) : null}
      <span className="truncate">{url}</span>
    </a>
  );
}
