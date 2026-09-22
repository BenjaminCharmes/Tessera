// Le point d'entrée `/vitest`, et non la racine : depuis jest-dom v7, c'est
// lui qui déclare les matchers sur l'`Assertion` de Vitest. Sans ce chemin,
// `toBeInTheDocument` et ses voisins existent à l'exécution mais restent
// invisibles pour `tsc` (ticket-118).
import "@testing-library/jest-dom/vitest";

// jsdom n'implémente pas scrollIntoView. Tout composant qui fait défiler vers
// un élément (le fil du chat, par exemple) plante sans ce comble — c'est un
// manque de l'environnement de test, pas du code testé.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView() {};
}
