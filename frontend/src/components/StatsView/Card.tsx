import type { ReactNode } from "react";
import RegionTitle from "../../design/RegionTitle";

/** Une carte du tableau : un titre de région, un contenu. */
export default function Card({
  title,
  aside,
  className = "",
  children,
}: {
  title: string;
  aside?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section
      aria-label={title}
      className={`min-w-0 rounded-xl border border-zinc-800/80 bg-zinc-900/70 p-5 shadow-sm shadow-black/30 ${className}`}
    >
      <header className="mb-4 flex items-baseline justify-between gap-2">
        <RegionTitle taille="sm">{title}</RegionTitle>
        {aside && <span className="text-micro text-zinc-500">{aside}</span>}
      </header>
      {children}
    </section>
  );
}
