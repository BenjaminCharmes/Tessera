import type { AnchorHTMLAttributes, ButtonHTMLAttributes } from "react";

/**
 * Bouton de la charte — ticket-439.
 *
 * Un seul `plein` (violet) par vue : l'action principale. Les autres sont
 * `borde` ou `discret`. Un `arret` est bordé de rouge, jamais plein : l'arrêt
 * se voit sans crier plus fort que l'action principale.
 */
export type VarianteBouton = "plein" | "borde" | "discret" | "arret";
export type TailleBouton = "normal" | "compact" | "pastille";

interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className"> {
  variante?: VarianteBouton;
  taille?: TailleBouton;
}

const VARIANTES: Record<VarianteBouton, string> = {
  plein: "bg-violet-500 text-white hover:bg-violet-400",
  borde: "border border-zinc-700 text-zinc-200 hover:border-zinc-500",
  discret: "text-zinc-400 hover:text-zinc-200",
  arret: "border border-red-500/60 text-red-300 hover:border-red-400",
};

const TAILLES: Record<TailleBouton, string> = {
  normal: "h-[30px] px-3 text-corps",
  compact: "h-[26px] px-2 text-corps",
  // À la hauteur d'une StatusPill, pour s'aligner sur les badges d'une même ligne.
  pastille: "h-5 px-2 text-mini font-medium",
};

/** Un lien qui a l'aspect d'un bouton : même variantes, même tailles. */
interface LienBoutonProps extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "className"> {
  variante?: VarianteBouton;
  taille?: TailleBouton;
  href: string;
}

function classes(variante: VarianteBouton, taille: TailleBouton): string {
  return `inline-flex max-w-full items-center justify-center gap-1.5 rounded transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTES[variante]} ${TAILLES[taille]}`;
}

export function LienBouton({ variante = "borde", taille = "normal", ...lien }: LienBoutonProps) {
  return <a className={classes(variante, taille)} {...lien} />;
}

export default function Button({
  variante = "borde",
  taille = "normal",
  type = "button",
  ...reste
}: ButtonProps) {
  return <button type={type} className={classes(variante, taille)} {...reste} />;
}
