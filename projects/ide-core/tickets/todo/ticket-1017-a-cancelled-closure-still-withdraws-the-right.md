---
id: ticket-1017
title: "A cancelled closure still withdraws the right and closes the job"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-1014"]
estimated_days: 1
created: 2026-11-19
---

## Signalement

- Audit sans contexte du 19/11, constat M1.

## Contexte

`services/providers/droits_appel.py`, `_clore_sous_verrou` : le compteur
`_ACTIFS` de la racine est retiré avant les attentes d'arrêt des processus,
de nettoyage et de retrait du droit. Une annulation pendant ces attentes
laisse le droit d'écriture du compte sur le worktree, sans compteur : plus
aucun appel ne le retire.

`services/providers/transport_agent.py`, `close` : si `super().close()`
lève, `process.aclose()` n'est pas appelé et le job reste ouvert.

Dans `ouvrir_appel`, une annulation entre `poser_ecriture` et l'incrément du
compteur laisse aussi le droit posé.

## Ce qu'il faut faire

- La clôture sous verrou va à son terme même si l'appelant est annulé
  (`asyncio.shield`), et l'annulation est relancée ensuite.
- `ouvrir_appel` : si une annulation ou une exception survient après
  `poser_ecriture` et avant l'incrément, le droit est retiré.
- `transport_agent.close` : `process.aclose()` dans un `finally`.

## Critères d'acceptation

- [ ] Test : une tâche annulée pendant `clore_appel` (faux `Icacls` qui
  attend) voit quand même `retirer_ecriture` aller à son terme, puis lève
  `CancelledError`.
- [ ] Test : une annulation juste après `poser_ecriture` dans `ouvrir_appel`
  ne laisse aucune entrée dans `_ACTIFS` et émet le retrait du droit.
- [ ] Test : quand `super().close()` lève, `aclose()` du processus est
  appelé.

## Ce que ça ne fait pas

- Ne change pas l'ordre des étapes de la clôture.
