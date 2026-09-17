import { useMemo } from "react";
import DOMPurify from "dompurify";
import { marked } from "marked";

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
 */
interface MarkdownViewProps {
  source: string;
}

export default function MarkdownView({ source }: MarkdownViewProps) {
  const html = useMemo(() => {
    const brut = marked.parse(source, { async: false }) as string;
    return DOMPurify.sanitize(brut, { USE_PROFILES: { html: true } });
  }, [source]);

  return (
    <div
      className="markdown-rendu h-full overflow-auto px-6 py-5 text-sm leading-relaxed text-zinc-300"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
