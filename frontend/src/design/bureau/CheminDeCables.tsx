import Tuile from "./Tuile";

/**
 * Le chemin de câbles du plafond (ticket-727) : un caillebotis à fils sur toute la
 * largeur du mur, câbles visibles entre les barreaux, une boucle qui pend. Un tronçon
 * de 80 × 16 qui se répète sans couture. Du mobilier : fixe, sans voyant.
 */
export default function CheminDeCables() {
  return (
    <div aria-hidden="true" className="relative h-6 w-full" data-sprite="chemin-de-cables">
      <Tuile motif="chemin" moment="jour" />
    </div>
  );
}
