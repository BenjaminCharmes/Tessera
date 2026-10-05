import { useMemo } from "react";
import DOMPurify from "dompurify";
import { marked } from "marked";
import { separerFrontmatter } from "./frontmatter";

/**
 * Un Markdown lu comme un document, pas comme du texte source — ticket-078.
 *
 * Les tickets, les ADR, `CLAUDE.md` et les notes de projet sont du Markdown :
 * les lire avec leurs `##` et leurs `**` demande un effort que le contenu ne
 * justifie pas.
 *
 * **Le HTML est assaini, pas rendu tel quel.** Ces fichiers sont écrits par des
 * agents : afficher leur HTML sans filtre donnerait à un texte généré le
 * pouvoir d'exécuter du script dans une application qui a accès au système de
 * fichiers. DOMPurify retire les balises actives et les schémas d'URL
 * exécutables, et laisse le reste.
 *
 * L'en-tête YAML s'affiche en fiche au-dessus du corps (ticket-334). Ses
 * valeurs passent par React, qui les échappe : elles ne touchent jamais au
 * HTML injecté.
 */
interface MarkdownViewProps {
  source: string;
}

export default function MarkdownView({ source }: MarkdownViewProps) {
  const { champs, corps } = useMemo(() => separerFrontmatter(source), [source]);
  const html = useMemo(() => {
    const brut = marked.parse(corps, { async: false }) as string;
    return DOMPurify.sanitize(brut, { USE_PROFILES: { html: true } });
  }, [corps]);

  return (
    <div className="h-full overflow-auto px-6 py-5 text-sm leading-relaxed text-zinc-300">
      {champs && champs.length > 0 && (
        <dl
          role="group"
          aria-label="En-tête du fichier"
          className="mb-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-0.5 rounded border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs"
        >
          {champs.map(([cle, valeur]) => (
            <div key={cle} className="contents">
              <dt className="text-zinc-500">{cle}</dt>
              <dd className="wrap-break-word font-mono text-zinc-300">{valeur}</dd>
            </div>
          ))}
        </dl>
      )}
      <div className="markdown-rendu" dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}
