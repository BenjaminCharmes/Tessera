interface NightVeilProps {
  /** La nuit sans lumière : le voile fonce. */
  sombre?: boolean;
}

/**
 * Le voile de nuit : une teinte sombre et légère sur la pièce, qui ne capte ni
 * clic ni survol. Il ne se monte que la nuit, à l'heure de la vue (ADR-058) ;
 * plus sombre quand l'interrupteur a éteint la salle. Le parent est `relative`.
 */
export default function NightVeil({ sombre = false }: NightVeilProps) {
  return (
    <div
      data-voile={sombre ? "nuit-sombre" : "nuit"}
      aria-hidden="true"
      className={`pointer-events-none absolute inset-0 z-30 rounded-lg ${sombre ? "bg-(--sprite-voile-sombre)" : "bg-(--sprite-voile)"}`}
    />
  );
}
