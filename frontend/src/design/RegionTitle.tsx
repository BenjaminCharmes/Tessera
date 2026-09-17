/**
 * Le titre d'une région de l'interface — ticket-067.
 *
 * Une barre d'accent le précède. Elle n'est pas décorative : c'est le seul
 * endroit où la teinte d'identité apparaît, et elle dit « ici commence une
 * région ». Les cinq familles de couleurs à rôle — rouge, ambre, vert, bleu,
 * neutre — restent réservées aux **états**, et une région n'en est pas un.
 *
 * C'est pour cela que l'accent est une barre et non la couleur du texte : du
 * violet sur un mot se lit comme un état, une barre devant un titre se lit
 * comme une structure.
 */
interface RegionTitleProps {
  children: React.ReactNode;
  /** `sm` dans une colonne de tableau, `md` en tête de panneau. */
  taille?: "sm" | "md";
}

export default function RegionTitle({
  children,
  taille = "md",
}: RegionTitleProps) {
  return (
    <span className="inline-flex items-center gap-2 align-middle">
      <span
        aria-hidden="true"
        className={`w-0.5 shrink-0 rounded-full bg-violet-400 ${
          taille === "md" ? "h-3.5" : "h-3"
        }`}
      />
      <span
        className={`font-semibold uppercase tracking-wider ${
          taille === "md" ? "text-xs text-zinc-300" : "text-mini text-zinc-400"
        }`}
      >
        {children}
      </span>
    </span>
  );
}
