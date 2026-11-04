"use strict";
/* Salle des serveurs : baie haute et climatiseur, grille ×2. Seul le voyant porte un état (ADR-058). */

/** La baie haute, 24 × 60 : sept serveurs 1U, un voyant à halo ; `activite` fait clignoter une diode par serveur. */
function baieHaute({ etat = "actif", activite = false } = {}) {
  const s = mk(24, 60), g = s.L(), M = P.metal, L = E(etat);
  g.rect(0, 0, 24, 60, M.d); g.rect(1, 1, 22, 58, M.b); g.rect(1, 1, 22, 1, M.hi); g.rect(1, 1, 1, 58, M.hi); g.rect(22, 2, 1, 57, M.s);
  g.rect(3, 3, 18, 6, M.d); g.rect(4, 4, 16, 4, P.frame.d); g.rect(5, 5, 7, 1, M.s); g.rect(5, 6, 4, 1, M.s);
  const v = s.L(); v.rect(16, 4, 4, 4, L.d); v.rect(17, 5, 2, 2, L.b); v.px(17, 5, L.hi);
  const leds = [];
  for (let i = 0; i < 7; i++) {
    const y = 12 + i * 6;
    g.rect(3, y, 18, 5, M.s); g.rect(4, y + 1, 16, 3, M.b); g.rect(4, y + 1, 16, 1, M.hi);
    for (let x = 7; x < 15; x += 2) g.px(x, y + 2, M.d);
    g.rect(3, y + 1, 1, 3, M.hi); g.rect(20, y + 1, 1, 3, M.d);
    if (activite && etat === "actif") leds.push(y); else g.px(17, y + 2, M.d);
  }
  leds.forEach((y, i) => s.L("clignote", `animation-delay:-${(i * .37) % 1.1}s;animation-duration:${.7 + (i % 3) * .35}s`).px(17, y + 2, L.hi));
  g.rect(2, 55, 20, 3, M.d); g.rect(3, 58, 3, 2, M.d); g.rect(18, 58, 3, 2, M.d);
  return s;
}
function climatiseur() {
  const s = mk(32, 44), g = s.L(), M = P.metal;
  g.rect(0, 0, 32, 44, M.d); g.rect(1, 1, 30, 42, M.b); g.rect(1, 1, 30, 1, M.hi); g.rect(1, 1, 1, 42, M.hi); g.rect(30, 2, 1, 41, M.s); g.rect(2, 42, 29, 1, M.s);
  g.rect(3, 3, 26, 26, M.d);
  for (let y = 4; y < 28; y += 3) { g.rect(4, y, 24, 1, M.hi); g.rect(4, y + 1, 24, 1, M.s); }
  g.rect(3, 31, 26, 9, M.s); g.rect(4, 32, 24, 1, M.d);
  for (let x = 5; x < 27; x += 2) g.rect(x, 34, 1, 4, M.d);
  g.rect(24, 3, 4, 2, M.s);
  return s;
}

enregistrer({ id: "baie", nom: "Baie haute, service en cours", fichier: "BaieHaute", salle: "serveurs", grille: "12 × 30 → 24 × 60", dw: 36, dh: 90,
  avant: () => avantBaie(), apres: () => baieHaute(), variante: { label: "Diodes d'activité", f: () => baieHaute({ activite: true }) },
  note: "Sept serveurs 1U avec poignées et grilles au lieu de sept traits. Le voyant a un halo ; la variante fait clignoter une diode par serveur tant que le service tourne." });
enregistrer({ id: "baie-echec", nom: "Baie haute, service en échec", fichier: "BaieHaute", salle: "serveurs", grille: "12 × 30 → 24 × 60", dw: 36, dh: 90,
  avant: () => avantBaie("blocage"), apres: () => baieHaute({ etat: "blocage" }),
  note: "Le rouge du voyant se lit de loin grâce au halo, sans gyrophare." });
enregistrer({ id: "clim", nom: "Climatiseur", fichier: "Climatiseur", salle: "serveurs", grille: "16 × 22 → 32 × 44", dw: 48, dh: 66,
  avant: () => avantClim(), apres: () => climatiseur(),
  note: "Des lames en relief (reflet dessus, ombre dessous), un filtre à fentes, une trappe de service." });
