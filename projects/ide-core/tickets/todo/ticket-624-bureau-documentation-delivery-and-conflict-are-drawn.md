---
id: ticket-624
title: "In the Bureau, documentation, delivery and conflict resolution are drawn"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-623]
estimated_days: 2
created: 2026-10-28
---

# ticket-624 — Documentation, livraison et conflit se voient dans le Bureau

## Objectif
Qu'aucune étape d'un run ne laisse la pièce vide ou trompeuse.

## Contexte
Le 28/10, Vigie était en « documentation » et sa pièce ne montrait que deux agents
à la machine à café. Trois étapes n'ont aucun poste : la documentation par lot
(ADR-035), la livraison (phase 1) et le résolveur de conflit (ADR-033).

Les événements existent :
- documentation : `documentation_started`, puis `doc_updated` ou
  `documentation_failed`. Sans fichier changé ni refus, aucun événement de fin
  n'est émis (`orchestrator.py`) : la documentation se termine alors au premier
  événement suivant du run qui n'en est pas un.
- livraison : `livraison_started` puis `livraison_done`.
- conflit : `conflict_resolution` avec `data.phase`, `data.files` et
  `data.outcome` (`livraison_evenements.py`), déjà lu par `etat.conflitEnCours`.

## Solution proposée
- **Documentation** : une salle commune « Bibliothèque » sur la rangée du haut,
  avec le sprite `Bibliotheque` existant. Pendant la documentation d'un projet,
  ses deux rédacteurs (technique et fonctionnel) s'y tiennent, et la liste de la
  salle porte le nom du projet. La salle est commune parce que la documentation
  se fait par lot, en fin de file, et non par ticket.
- **Livraison** : entre `livraison_started` et `livraison_done`, le codeur se tient
  devant la boîte aux lettres de sa pièce, avec l'activité « dépose la PR ».
- **Conflit** : pendant une résolution, un agent « Résolveur » avec sa propre tenue
  se tient à la table de la salle de réunion, à côté de la liste des fichiers
  déjà affichée.

## Critères d'acceptation
- [ ] Un test vérifie qu'un projet est listé dans la salle « Bibliothèque » après `documentation_started`, et n'y est plus après `doc_updated`, après `documentation_failed`, ni après un `livraison_started` qui suit
- [ ] Un test vérifie que la salle « Bibliothèque » est vide quand aucun projet ne documente
- [ ] Un test de `lib/bureau/activites.ts` vérifie qu'entre `livraison_started` et `livraison_done` l'activité du codeur est « dépose la PR », ancrée à la boîte aux lettres
- [ ] `lib/bureau/physique.ts` donne une tenue au résolveur, et un test vérifie que la salle de réunion le dessine pendant un `conflict_resolution` sans `outcome`, et ne le dessine plus après
- [ ] Les nouvelles tenues n'utilisent que des jetons `--sprite-*` (ADR-058)

## Ce que ça ne fait pas
- Ne touche pas au backend.
- Ne change pas la salle de pause : c'est le ticket-625.
