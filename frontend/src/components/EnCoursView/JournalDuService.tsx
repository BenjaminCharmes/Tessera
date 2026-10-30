import { useEffect, useMemo, useRef, useState } from "react";
import type { ServiceActif } from "../../types/api";
import Button from "../../design/ui/Button";
import { libelleDeLEtat } from "../../design/etatDuService";
import { niveauDeLigne, TON_DE_LIGNE } from "./journal";

interface JournalDuServiceProps {
  projectName: string;
  service: ServiceActif;
  onFermer: () => void;
}

type Filtre = "tout" | "erreurs";

/**
 * Le journal déplié d'un service — ticket-711 : toutes les lignes gardées par le
 * backend, filtrables, cherchables, et qui suivent la fin tant qu'on le demande.
 * Il s'ouvre sous la salle, dans sa carte : la salle reste visible au-dessus.
 */
export default function JournalDuService({ projectName, service, onFermer }: JournalDuServiceProps) {
  const [filtre, setFiltre] = useState<Filtre>("tout");
  const [recherche, setRecherche] = useState("");
  const [suivre, setSuivre] = useState(true);
  const fin = useRef<HTMLDivElement>(null);
  const sortie = useMemo(() => service.sortie ?? [], [service.sortie]);

  const lignes = useMemo(() => {
    const cherche = recherche.trim().toLowerCase();
    return sortie
      .map((texte, index) => ({ texte, numero: index + 1, niveau: niveauDeLigne(texte) }))
      .filter((l) => filtre === "tout" || l.niveau === "erreur")
      .filter((l) => cherche === "" || l.texte.toLowerCase().includes(cherche));
  }, [sortie, filtre, recherche]);
  const erreurs = sortie.filter((l) => niveauDeLigne(l) === "erreur").length;

  useEffect(() => {
    const zone = fin.current?.parentElement;
    if (suivre && zone) zone.scrollTop = zone.scrollHeight;
  }, [suivre, lignes]);

  useEffect(() => {
    const surTouche = (e: KeyboardEvent) => e.key === "Escape" && onFermer();
    window.addEventListener("keydown", surTouche);
    return () => window.removeEventListener("keydown", surTouche);
  }, [onFermer]);

  return (
    <section
      id={`journal-${service.project_id}-${service.nom}`}
      aria-label={`Journal de ${projectName} · ${service.nom}`}
      data-journal={service.nom}
      className="flex flex-col border-t border-violet-700 bg-zinc-950"
    >
      <header className="flex flex-wrap items-center gap-3 border-b border-zinc-800 px-4 py-3">
        <h2 className="text-sm font-semibold text-zinc-100">
          {projectName} · {service.nom}
        </h2>
        <span className="text-xs text-zinc-400">{libelleDeLEtat(service)}</span>
        <span className="ml-auto flex gap-2">
          <Button taille="compact" onClick={() => void navigator.clipboard?.writeText(sortie.join("\n"))}>
            Copier
          </Button>
          <Button taille="compact" onClick={onFermer} aria-label="Fermer le journal">
            Fermer
          </Button>
        </span>
      </header>
      <div className="flex flex-wrap items-center gap-2 border-b border-zinc-800 px-4 py-2 text-xs">
        <div role="group" aria-label="Filtrer" className="flex gap-1">
          {(["tout", "erreurs"] as const).map((f) => (
            <button
              key={f}
              type="button"
              aria-pressed={filtre === f}
              onClick={() => setFiltre(f)}
              className={`rounded-sm px-2 py-1 ring-1 ring-zinc-700 ${filtre === f ? "bg-zinc-700 text-zinc-100" : "text-zinc-400 hover:text-zinc-200"}`}
            >
              {f === "tout" ? `Tout · ${sortie.length}` : `Erreurs · ${erreurs}`}
            </button>
          ))}
        </div>
        <input
          type="search"
          aria-label="Chercher dans le journal"
          placeholder="Chercher…"
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
          className="min-w-0 flex-1 rounded-sm bg-zinc-900 px-2 py-1 text-zinc-200 ring-1 ring-zinc-700 placeholder:text-zinc-500"
        />
        <label className="flex items-center gap-1 text-zinc-400">
          <input type="checkbox" checked={suivre} onChange={(e) => setSuivre(e.target.checked)} />
          Suivre la fin
        </label>
      </div>
      <div className="h-80 overflow-auto py-2 font-mono text-xs leading-relaxed">
        {lignes.map((l) => (
          <div
            key={l.numero}
            className={`grid grid-cols-[3.5rem_1fr] gap-3 px-4 ${l.niveau === "erreur" ? "bg-red-950/40" : ""}`}
          >
            <span className="text-right text-zinc-600">{l.numero}</span>
            <span className={`whitespace-pre-wrap break-words ${TON_DE_LIGNE[l.niveau]}`}>{l.texte}</span>
          </div>
        ))}
        {lignes.length === 0 && <p className="px-4 text-zinc-500">Aucune ligne.</p>}
        <div ref={fin} />
      </div>
      <footer className="border-t border-zinc-800 px-4 py-2 text-micro text-zinc-500">
        Les 200 dernières lignes gardées par Tessera (sortie et erreurs du service).
      </footer>
    </section>
  );
}
