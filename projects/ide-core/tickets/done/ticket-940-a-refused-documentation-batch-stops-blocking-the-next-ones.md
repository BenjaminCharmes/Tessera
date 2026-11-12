---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 0.5
id: ticket-940
pr_number: null
priority: high
status: done
title: A documentation batch refused twice leaves the queue instead of blocking every
  later batch
type: fix
---

# ticket-940 — Un lot de documentation refusé deux fois sort de la file au lieu de bloquer tous les suivants

## Objectif

Qu'un lot de documentation que les contrôles d'ADR-057 refusent ne soit pas
retenté à chaque run, pour toujours, en empêchant les tickets suivants d'être
documentés.

## Contexte

Constaté sur Curio le 12/11. `memory/documentation.json` s'arrêtait à
`ticket-030` jusqu'au run du ticket-091 (11/11). Pendant ce temps, une soixantaine de runs
approuvés ont reçu le même refus : « règle « preuve » », « règle « jeton
vérifiable » » (journal du 11/11, tickets 088 à 092). La doc technique n'a
plus bougé depuis le ticket-030, et le guide une seule fois.

La mécanique, dans `services/documentation/documentation.py` :

- `mettre_a_jour` garde les `_PLAFOND` (5) tickets non documentés **les plus
  anciens** (ticket-541) ;
- quand toutes les éditions sont refusées, même après le tour de correction
  (ticket-395), le marqueur n'avance pas : « on réessaiera au prochain run »
  (ticket-213) ;
- le run suivant renvoie donc le même lot de vieux tickets. Leur diff ne
  correspond plus au code d'aujourd'hui, l'agent recopie le code actuel
  (ex. `frontend/src/screens/pairs-deal.ts`, touché par 031 et 051, qui n'est
  pas dans la matière), et la règle « preuve » refuse encore. Rien ne
  s'arrête.

Les contrôles ont raison de refuser : le défaut est que le refus se répète
sans fin, sans que personne ne le voie.

Second défaut, plus petit : le motif écrit dans `memory/pipeline-log.md`
s'arrête au premier saut de ligne de l'extrait cité. On lit « l'extrait
« export const PAIRS_FETCH = 40; » sans le fichier ni la raison.

## Solution proposée

1. `documentation.json` compte les refus par ticket, sous une clé `refus`
   (`{"ticket-036": 1}`), à côté de `documentes`. Les deux formats déjà
   connus restent lisibles (ADR-036).
2. Un lot entièrement refusé incrémente le compteur de chacun de ses
   tickets. Au **deuxième** refus, ces tickets passent dans une liste
   `abandonnes` : `tickets_a_documenter` ne les renvoie plus, et le lot
   suivant passe aux tickets plus récents.
3. L'abandon se voit : une ligne dans `memory/pipeline-log.md` (« documentation
   abandonnée pour ticket-036, ticket-037… après 2 refus ») et le champ du
   `ResultatDocumentation` que l'orchestrateur journalise déjà pour les écartés.
4. Le motif d'un refus est écrit sur une seule ligne dans le journal : les
   sauts de ligne de l'extrait deviennent des espaces.

## Critères d'acceptation

- [ ] Un test : un lot dont toutes les éditions sont refusées une première
      fois → `refus` vaut 1 pour chacun de ses tickets, et ils restent à
      documenter.
- [ ] Un test : le même lot refusé une deuxième fois → ses tickets sont dans
      `abandonnes`, et `tickets_a_documenter` renvoie les tickets suivants.
- [ ] Un test : un lot qui applique au moins une édition → ses tickets
      passent dans `documentes` et sortent de `refus`.
- [ ] Un test : un `documentation.json` sans `refus` ni `abandonnes`
      (format actuel) et un fichier à l'ancien format `dernier_ticket` sont
      encore lus.
- [ ] Un test : un motif dont l'extrait contient un saut de ligne est écrit
      sur une seule ligne dans `memory/pipeline-log.md`.
- [ ] Les fichiers touchés restent sous 300 lignes (`documentation.py` en
      fait 401 : la logique de refus vit dans `documentation_selection.py`
      ou dans un module voisin, sans faire grossir `documentation.py`).

## Ce que ça ne fait pas

- Ne relâche ni la règle « preuve » ni la règle « jeton vérifiable »
  (ADR-057) : un refus reste un refus.
- Ne passe pas à l'application édition par édition : une doc à moitié à jour
  reste pire qu'une doc en retard (`appliquer_editions`).
- Ne rattrape pas le retard de Curio : les tickets abandonnés ne sont pas
  documentés. Un rattrapage se fera par un ticket `docs` du projet.
- Ne change ni `_PLAFOND` ni l'ordre du lot (ticket-541).

## Dépendances

Aucune.