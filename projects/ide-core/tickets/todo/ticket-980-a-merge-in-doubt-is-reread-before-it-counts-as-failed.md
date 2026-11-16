---
agent: codeur
created: '2026-11-16'
depends_on: []
id: ticket-980
priority: high
status: todo
title: Un merge douteux se relit pendant deux minutes avant de compter comme un échec
type: fix
---

## Signalement

- Projet source : vigie (session Vigie, 16/11 ; aussi déposé par
  `POST /signalements`, réponse en attente : le ticket qu'il produira est un
  doublon de celui-ci, à passer en `cancelled`)
- Nature : bug

## Contexte

Vigie, file `52d36fc1`, 16/11 à 11:08:44 UTC. La livraison du ticket-104
s'arrête : « PR #145 non mergée : erreur réseau (ReadTimeout, la PR est lue
« open ») ». Dans la même seconde, « ticket-108 sauté : dépend de
ticket-104, non mergé ». Quelques minutes plus tard, #145 est MERGED. GitHub
renvoyait alors des 502 et des « Merge already in progress » (vus aussi avec
`gh pr merge`).

Cause, dans `services/livraison/livraison_merge.py` :

- `relire_apres_erreur_reseau` relit l'état de la PR **une seule fois**, tout
  de suite après l'erreur. Un merge que GitHub est en train de faire se lit
  encore `open`.
- `tenter_le_merge` traite tout `httpx.HTTPStatusError` comme un refus,
  jamais relu. Or un 5xx, ou un 405 « Merge already in progress », est un
  doute, pas un verdict.

## Ce qu'il faut faire

1. `relire_apres_erreur_reseau` relit la PR plusieurs fois pendant une
   fenêtre bornée (par défaut 120 s, toutes les 15 s, valeurs injectables
   pour les tests) tant qu'elle se lit `open`. `merged` → mergée, confirmée
   après erreur. `closed`, ou toujours `open` à la fin de la fenêtre, ou
   relecture impossible → arrêt comme aujourd'hui (ADR-039, échec fermé).
2. `tenter_le_merge` traite comme un doute, relu de la même façon : un
   `HTTPStatusError` de statut 5xx, et un statut 405 dont le corps contient
   « Merge already in progress ». Les autres statuts (405 « not mergeable »,
   409 tête changée, 422…) restent des refus, sans relecture.
3. `arret_de_merge` dit, pour un doute qui n'a pas abouti, combien de temps
   la PR a été relue.

## Critères d'acceptation

- [ ] Test : `ReadTimeout`, puis la PR se lit `open`, `open`, `merged` →
      `IssueMerge(merged=True, confirme_apres_reseau=True)`.
- [ ] Test : `ReadTimeout`, puis `open` jusqu'au bout de la fenêtre →
      `merged=False`, avec l'erreur et la durée de relecture dans l'arrêt.
- [ ] Test : un 502 au merge, puis `merged` à la relecture → mergée.
- [ ] Test : un 405 « Merge already in progress », puis `merged` → mergée.
- [ ] Test : un 405 « Pull Request is not mergeable » → refus, aucune
      relecture.
- [ ] Test : `closed` à la relecture → arrêt immédiat, sans attendre la fin
      de la fenêtre.
- [ ] Test : la fenêtre et l'intervalle sont injectés : aucun test ne dort
      réellement.

## Ce que ça ne fait pas

- Ne change pas la règle qui saute un ticket dépendant d'un ticket non
  mergé : elle devient juste, car un merge abouti n'est plus compté comme
  un échec.
- Ne relance pas le merge : on relit, on ne retente pas (un second merge sur
  une PR mergée est un refus de GitHub, pas un succès).
