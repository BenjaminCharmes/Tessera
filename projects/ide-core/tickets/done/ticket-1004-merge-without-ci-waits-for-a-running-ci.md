---
agent: codeur
depends_on: []
id: ticket-1004
preuve_reelle: false
priority: high
status: done
title: A project that merges without CI still waits for a CI that is running
type: fix
---

## Signalement

Preuve Serpent 009 du 18/11 (run `3f5f4b62`) : run approuvé, PR serpent #16
ouverte, puis `ci_watcher_blocked — GitHub a refusé le merge de la PR #16`
et la fiche passe en `blocked`. Journal : `merge_refuse … "ci": "pending"`.

## Contexte

Serpent déclare `merge_without_ci: true` mais porte un workflow
(`.github/workflows/ci.yml`, check `verifier`). Avec `merge_without_ci`,
`livraison.py` saute `_attendre_la_ci` et appelle `_merger` aussitôt
(« CI : non attendue, déclarée absente »). `merge_si_la_ci_est_verte` relit
alors l'état : le check vient de s'inscrire, `pending`, et
`niveau_peut_merger` refuse, à raison (ADR-045 : « pas de CI » ne veut pas
dire « ignore la CI »). Le refus devient l'arrêt « GitHub a refusé le
merge », qui est faux : GitHub n'a rien refusé, c'est Tessera qui n'a pas
attendu.

## Ce qu'il faut faire

- Avec `merge_without_ci`, attendre quand même un verdict tant que la CI de
  la PR est `pending` (la même borne que `_attendre_la_ci`). `none` reste le
  seul état qui autorise le merge sans verdict, comme aujourd'hui.
- Un merge que Tessera n'a pas tenté (refus de `niveau_peut_merger`) ne
  s'écrit jamais « GitHub a refusé le merge » : l'arrêt dit l'état de la CI.

## Critères d'acceptation

- [ ] Test : `merge_without_ci`, CI `pending` puis `passing` → la PR est
  mergée, sans arrêt.
- [ ] Test : `merge_without_ci`, CI `pending` puis `failing` → pas de merge,
  arrêt qui nomme la CI rouge.
- [ ] Test : `merge_without_ci`, CI `none` → merge immédiat, comme avant.
- [ ] Test : un refus de `niveau_peut_merger` ne produit pas l'arrêt
  « GitHub a refusé le merge ».

## Ce que ça ne fait pas

- Ne change pas `niveau_peut_merger` : une CI `pending` ou `failing` refuse
  toujours le merge.
- Ne touche pas aux projets sans `merge_without_ci`.