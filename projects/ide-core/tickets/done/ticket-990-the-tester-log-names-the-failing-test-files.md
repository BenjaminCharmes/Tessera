---
agent: codeur
depends_on: []
id: ticket-990
pr_number: 1164
priority: medium
status: done
title: The tester log names the failing test files
type: fix
---

## Signalement

- Projet source : vigie (session Vigie, relayé par l'Orchestrateur le 17/11)
- Nature : bug d'observabilité : un test échoue au tour 1 puis passe sans
  changement, et le journal ne dit pas lequel

## Contexte

Vigie ticket-115, 17/11 : un test backend échoue au tour 1, puis passe au
tour 2 sans que le code l'ait touché. `pipeline-log.md` ne porte que la ligne
de résumé (`testeur: 1 failed, 999 passed …`, `pipeline_testeur.py`, ligne
`orch._log(f"[…] testeur: {result.output_summary}")`) : impossible de savoir
quel test est fragile sans relire la sortie complète, qui n'est pas gardée
dans le journal.

Le ticket-971 a ajouté `relance_instable.lire_les_echecs(sortie)`, qui lit les
fichiers en échec d'une sortie pytest ou vitest : il ne sert qu'à la relance.

## Ce qu'il faut faire

- Quand les tests sont rouges, la ligne du testeur dans le journal nomme les
  fichiers en échec lus par `lire_les_echecs`, dédoublonnés, au plus cinq,
  suivis de « +N » s'il y en a davantage.
- Rien de plus quand aucun fichier n'est lu (sortie d'un autre outil : tsc,
  eslint) ; la ligne reste celle d'aujourd'hui.

## Critères d'acceptation

- [ ] Test : sortie pytest avec deux tests en échec dans un même fichier et un
      dans un autre — la ligne nomme les deux fichiers une fois chacun.
- [ ] Test : sortie vitest avec sept fichiers en échec — cinq nommés, « +2 ».
- [ ] Test : sortie sans fichier lisible — ligne inchangée.

## Ce que ça ne fait pas

- Ne relance pas un échec d'assertion intermittent : seul un test qui n'a fait
  qu'expirer est relancé (ticket-971).
- Ne garde pas la sortie complète des tests dans le journal.