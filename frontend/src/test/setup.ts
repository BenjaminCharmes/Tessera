import "@testing-library/jest-dom";

// jsdom n'implémente pas scrollIntoView. Tout composant qui fait défiler vers
// un élément (le fil du chat, par exemple) plante sans ce comble — c'est un
// manque de l'environnement de test, pas du code testé.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView() {};
}
