---
agent: codeur
created: 2026-09-28
depends_on: []
estimated_days: 1
id: ticket-213
pr_number: null
priority: high
status: done
title: La mise à jour de la doc est bornée, et son échec se voit
type: fix
---

# ticket-213 — Un lot de doc borné et visible

## Objectif

La mise à jour de la documentation après un run approuvé ne bloque jamais le
run sur un lot démesuré. Quand elle échoue, l'échec apparaît à l'écran au lieu
de rester dans les logs du serveur.

## Contexte

`tickets_a_documenter` renvoie tous les tickets terminés dont l'identifiant
dépasse le marqueur `memory/documentation.json`, et **tous** les tickets
terminés quand ce marqueur n'existe pas. Sur `ide-core`, qui n'en avait pas,
le premier run approuvé a envoyé 201 tickets, soit environ 190 000 tokens,
à `qwen3-coder:30b`. Après 5 minutes (`DELAI_LECTURE_S`), l'appel a échoué à
13 % du traitement du prompt. `_documenter_le_run` a avalé l'exception
(`_logger.warning("documentation_echouee")`, sans événement), le marqueur n'a
pas été écrit, et chaque run approuvé suivant aurait perdu les mêmes
5 minutes. Pendant ce temps, l'IDE refusait tout réglage avec un 409, sans
dire pourquoi le run durait.

Un marqueur a été posé à la main sur `ticket-205` pour débloquer.

Autre défaut : un ticket terminé **après** un ticket de numéro plus élevé
n'est jamais documenté, parce que le filtre compare des identifiants
(`identifiant <= dernier`), pas des dates de livraison.

## Solution proposée

1. **Sans marqueur, pas de rattrapage** : le service pose le marqueur sur le
   plus grand ticket terminé et ne documente rien. Un projet qui n'a jamais eu
   de doc automatique ne la reçoit pas d'un coup.
2. **Un plafond** : au-delà de N tickets (constante, 10 par exemple), on ne
   garde que les N plus récents, et l'événement le dit.
3. **Un échec visible** : l'exception attrapée dans `_documenter_le_run` émet
   un événement (`documentation_failed`, avec la cause) sur le canal
   d'ADR-041, que l'UI affiche dans le journal du run.
4. **Le marqueur devient la liste des tickets déjà documentés**, pas un
   plafond d'identifiant. Il faut garder la lecture de l'ancien format
   `{"dernier_ticket": …}` (ADR-036).

## Critères d'acceptation

- [ ] Un test : projet sans `documentation.json` avec 3 tickets terminés →
      aucun appel au provider, et le marqueur est créé
- [ ] Un test : 15 tickets à documenter → le brief n'en contient que 10, et
      l'événement le signale
- [ ] Un test : un provider qui lève → un événement `documentation_failed`
      est émis avec la cause, et le run reste approuvé
- [ ] Un test : `ticket-208` terminé après `ticket-209` déjà documenté →
      `ticket-208` figure dans le lot suivant
- [ ] Un `documentation.json` à l'ancien format est encore lu
- [ ] Un test : lot dont toutes les éditions sont refusées → le marqueur n'avance pas
- [ ] Un test : le marqueur réécrit est commité avec la doc, ou n'est pas versionné, et l'arbre reste propre avant la livraison
- [ ] L'UI affiche `documentation_failed` dans le journal du run (test Vitest)
- [ ] `uv run pytest` et `npm run test` passent

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Changer le format du marqueur touche des projets dont ce dépôt ne versionne
pas le `memory/`. D'où la lecture obligatoire de l'ancien format.