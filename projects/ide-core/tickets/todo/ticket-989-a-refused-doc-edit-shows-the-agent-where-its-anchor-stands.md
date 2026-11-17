---
id: ticket-989
title: "A refused doc edit shows the agent where its anchor stands"
type: fix
status: todo
priority: medium
agent: codeur
depends_on: []
---

## Signalement

- Projet source : vigie (session Vigie, relayé par l'Orchestrateur le 17/11)
- Nature : bug : la documentation d'un ticket refusée deux fois le même jour,
  tour de correction compris

## Contexte

`services/documentation/documentation_editions.py`, `_localiser` : une édition
`remplacer` dont l'ancien texte est absent du fichier, ou présent plusieurs
fois, lève `EditionRefusee`. Le tour de correction (ticket-395,
`documentation_titres.brief_correction`) rappelle l'agent avec le motif et les
titres des fichiers visés — mais pas avec le texte autour de l'ancre. L'agent
recommence donc à l'aveugle :

- Vigie ticket-113, 17/11 08:59 UTC : `docs/architecture.md : texte
  introuvable — « Les dépendances de Tessera sont déclarées dans … »`, refusé
  après correction ;
- Vigie ticket-115, 17/11 11:38 UTC : `docs/guide-utilisateur.md : texte
  présent 2 fois — on ne devine pas laquelle remplacer`, refusé après
  correction.

## Ce qu'il faut faire

- `EditionRefusee` porte, en plus du message, un extrait du fichier visé :
  - texte introuvable : le passage le plus proche de l'ancien texte (même
    nombre de lignes, choisi par ressemblance, `difflib`), s'il dépasse un
    seuil de ressemblance ; sinon rien ;
  - texte présent N fois : chaque occurrence avec deux lignes avant et après,
    numérotées, pour que l'agent allonge son ancre jusqu'à la rendre unique.
- `brief_correction` ajoute cet extrait au motif, borné (au plus 3 000
  caractères), sous un titre qui dit ce que l'agent doit en faire.
- Le message du journal du pipeline ne change pas.

## Critères d'acceptation

- [ ] Test : ancre introuvable mais proche d'un passage (une phrase réécrite)
      — le brief de correction contient ce passage.
- [ ] Test : ancre présente deux fois — le brief contient les deux
      occurrences avec leur contexte et leurs numéros de ligne.
- [ ] Test : ancre sans aucun passage ressemblant — le brief ne contient pas
      d'extrait.
- [ ] Test : l'extrait est borné à 3 000 caractères.

## Ce que ça ne fait pas

- Ne choisit pas l'occurrence à la place de l'agent : deux occurrences restent
  un refus (ADR-057).
- N'ajoute pas de second tour de correction.
