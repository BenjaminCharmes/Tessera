/** Cinq tons de confettis, écrits en toutes lettres pour que Tailwind les repère. */
const TONS = [
  "bg-(--sprite-confetti-1)",
  "bg-(--sprite-confetti-2)",
  "bg-(--sprite-confetti-3)",
  "bg-(--sprite-confetti-4)",
  "bg-(--sprite-confetti-5)",
] as const;

/** Dix-huit confettis de 4 × 6 px, comme dans la maquette. */
const NOMBRE = 18;
const LARGEUR_DU_SOL = 800;

/** Abscisse et hauteur de départ de chaque confetti : répartis, pas aléatoires. */
function depart(i: number): { left: number; top: number; delai: number } {
  return {
    left: (i * 47 + 20) % (LARGEUR_DU_SOL - 8),
    top: (i * 29) % 70,
    delai: -(i % 6) * 0.25,
  };
}

/**
 * Les confettis d'une PR mergée : ils tombent le temps de la fête. Sous
 * `prefers-reduced-motion` ils ne tombent plus et restent là où ils ont été lâchés.
 */
export default function Confettis() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-20 overflow-hidden">
      {Array.from({ length: NOMBRE }, (_, i) => {
        const { left, top, delai } = depart(i);
        return (
          <span
            key={i}
            data-sprite="confetti"
            className={`anim-chute absolute h-1.5 w-1 ${TONS[i % TONS.length]}`}
            style={{ left, top, animationDelay: `${delai}s` }}
          />
        );
      })}
    </div>
  );
}
