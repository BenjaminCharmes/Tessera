/**
 * Le voile de nuit : une teinte sombre et légère sur la pièce, qui ne capte ni
 * clic ni survol. Il ne se monte que la nuit, à l'heure de la vue (ADR-058) ;
 * le parent est `relative`.
 */
export default function NightVeil() {
  return (
    <div
      data-voile="nuit"
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 z-30 rounded-lg bg-(--sprite-voile)"
    />
  );
}
