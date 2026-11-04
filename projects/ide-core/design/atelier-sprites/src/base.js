"use strict";
/* Les jetons d'une famille, sous la forme qu'attendent les fonctions de dessin. */
const R = fam => ({ hi: fam + ".hi", b: fam + ".b", s: fam + ".s", d: fam + ".d", bl: fam + ".bl" });
const ROLES = ["codeur", "reviewer", "testeur", "securite", "validateur", "architect", "resolveur", "doc-technique", "doc-fonctionnelle"];
const P = {
  skin: [1, 2, 3, 4, 5].map(i => R("peau" + i)),
  hair: [1, 2, 3, 4, 5, 6].map(i => R("cheveux" + i)),
  top: Object.fromEntries(ROLES.map(r => [r, R("haut-" + r)])),
  pants: R("pantalon"), shoe: R("chaussure"), desk: R("bureau"), chair: R("chaise"), clavier: R("clavier"),
  metal: R("metal"), frame: R("cadre"), plant: R("plante"), pot: R("pot"), soil: R("terre"), cactus: R("cactus"),
  potClair: R("pot-clair"), machine: R("machine"), cup: R("tasse"), wood: R("bois"),
  books: [1, 2, 3].map(i => R("livre" + i)), col: R("col"), cravate: R("cravate"), flower: R("fleur"),
  sueur: R("sueur"), ink: "encre.b", coffee: "cafe.b", spine: "epine.b",
};
/** Les jetons d'un état : voyants, écrans. Jamais thémés. */
const E = etat => R("etat-" + etat);

/** Le physique de quelques agents d'exemple, comme `physique(projet, rôle)` en tirerait. */
const PH = {
  codeur: { peau: 2, cheveux: 1, coiffure: "court" },
  reviewer: { peau: 4, cheveux: 2, coiffure: "long" },
  testeur: { peau: 1, cheveux: 3, coiffure: "carre", jupe: true },
  securite: { peau: 5, cheveux: 6, coiffure: "chauve" },
  validateur: { peau: 3, cheveux: 4, coiffure: "court" },
  architect: { peau: 2, cheveux: 5, coiffure: "carre" },
};

/**
 * Le registre des sprites. Chaque entrée : id, nom, fichier (composant Tessera visé),
 * salle, grille (« avant → après »), dw × dh (taille réelle en px), avant() (copie
 * fidèle, couleurs fixes) ou null pour un sprite nouveau, apres(opts) (jetons), note.
 */
const REGISTRE = [];
const enregistrer = def => { REGISTRE.push(def); return def; };
const sprite = id => REGISTRE.find(d => d.id === id);
