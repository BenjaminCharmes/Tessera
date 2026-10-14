import { lazy, Suspense, useEffect, useRef, useState } from "react";
import RegionTitle from "../../design/RegionTitle";
import { BAND } from "../../design/layout";
import EtatVide from "./EtatVide";
import { ticketDuDernierRun } from "./touches";
import type { Project, Ticket, TicketStatus } from "../../types/api";

// Monaco ne se charge que quand un fichier ou un diff s'affiche (ticket-355).
const Editor = lazy(() => import("../Editor"));
const DiffView = lazy(() => import("../DiffView"));

type Mode = "editeur" | "diff";

interface FichiersViewProps {
  project: Project | null;
  /** Le ticket sélectionné : c'est de lui que vient « Diff du ticket ». */
  ticket: Ticket | null;
  byStatus: Record<TicketStatus, Ticket[]>;
  openFilePath: string | null;
  onOpenFile: (path: string) => void;
  onCloseFile: () => void;
}

const MODES: { mode: Mode; libelle: string }[] = [
  { mode: "editeur", libelle: "Éditeur" },
  { mode: "diff", libelle: "Diff du ticket" },
];

/**
 * Le centre de l'onglet Fichiers — ticket-428.
 *
 * Il tombait sur la liste des tickets quand aucun fichier n'était ouvert : un
 * onglet « Fichiers » qui montrait des tickets. Il a maintenant sa vue :
 * l'éditeur ou le diff du ticket, et, sans fichier ouvert, de quoi en ouvrir un.
 */
export default function FichiersView({
  project,
  ticket,
  byStatus,
  openFilePath,
  onOpenFile,
  onCloseFile,
}: FichiersViewProps) {
  const [mode, setMode] = useState<Mode>("editeur");
  const champRef = useRef<HTMLInputElement>(null);
  const focusDemande = useRef(false);
  const [, redessiner] = useState(0);

  // Ouvrir un fichier depuis l'arbre pendant qu'on lit un diff doit le montrer :
  // le mode se recale dès que le fichier ouvert change.
  const [dernierOuvert, setDernierOuvert] = useState(openFilePath);
  if (dernierOuvert !== openFilePath) {
    setDernierOuvert(openFilePath);
    if (openFilePath) setMode("editeur");
  }

  // Ctrl+P : cette vue n'existe que quand l'onglet Fichiers est actif, donc
  // le raccourci ne s'arme que là.
  useEffect(() => {
    const surTouche = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey) || e.key.toLowerCase() !== "p") return;
      e.preventDefault();
      setMode("editeur");
      if (openFilePath) onCloseFile();
      focusDemande.current = true;
      redessiner((n) => n + 1);
    };
    window.addEventListener("keydown", surTouche);
    return () => window.removeEventListener("keydown", surTouche);
  }, [openFilePath, onCloseFile]);

  // Le champ n'existe qu'une fois le fichier refermé : on attend qu'il soit
  // monté pour y mettre le focus.
  useEffect(() => {
    if (focusDemande.current && champRef.current) {
      champRef.current.focus();
      focusDemande.current = false;
    }
  });

  return (
    <div className="flex h-full flex-col bg-zinc-900">
      <div className={`${BAND} justify-between gap-2 border-b border-zinc-700 px-4`}>
        <RegionTitle>Fichiers</RegionTitle>
        {openFilePath && mode === "editeur" && (
          <button
            type="button"
            onClick={onCloseFile}
            className="ml-auto text-xs text-zinc-400 transition-colors hover:text-zinc-200"
          >
            Fermer le fichier
          </button>
        )}
        <div
          role="group"
          aria-label="Vue"
          className="flex rounded-md border border-zinc-800 bg-zinc-900 p-0.5"
        >
          {MODES.map(({ mode: m, libelle }) => (
            <button
              key={m}
              type="button"
              aria-pressed={mode === m}
              onClick={() => setMode(m)}
              className={`rounded px-3 py-1 text-xs transition-colors ${
                mode === m
                  ? "bg-zinc-700 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {libelle}
            </button>
          ))}
        </div>
      </div>
      <Suspense
        fallback={<p className="px-4 py-3 text-xs text-zinc-500">Chargement…</p>}
      >
        {project === null ? (
          <p className="px-4 py-3 text-xs text-zinc-500">
            Sélectionne un projet pour parcourir ses fichiers.
          </p>
        ) : mode === "diff" ? (
          ticket ? (
            <DiffView projectId={project.id} ticketId={ticket.id} />
          ) : (
            <p className="px-4 py-3 text-xs text-zinc-500">
              Sélectionne un ticket pour voir son diff
            </p>
          )
        ) : openFilePath ? (
          <div className="min-h-0 flex-1">
            <Editor ticket={null} openFilePath={openFilePath} projectId={project.id} />
          </div>
        ) : (
          <EtatVide
            key={project.id}
            project={project}
            ticketTouche={ticketDuDernierRun(ticket, byStatus)}
            onOpenFile={onOpenFile}
            champRef={champRef}
          />
        )}
      </Suspense>
    </div>
  );
}
