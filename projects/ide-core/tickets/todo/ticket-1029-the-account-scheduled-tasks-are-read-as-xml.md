---
id: ticket-1029
title: "The account scheduled tasks are read as XML"
type: refactor
status: todo
priority: medium
agent: codeur
depends_on: []
preuve_reelle: true
---

# ticket-1029 — Les tâches planifiées du compte se lisent en XML

## Objectif

Remplacer la lecture `schtasks /query /fo csv /nh /v` (2,0 s sous le compte) par
`/query /xml` (0,2 s, mesure du 20/11), sans rien retirer de la fermeture du
ticket-1018.

## À faire

**`taches_compte.py`**

- `_supprimer_les_taches` lance `schtasks /query /xml` ; les arguments restent
  fixés dans le module.
- `taches_du_compte` lit le XML : le nom vient du commentaire qui précède chaque
  tâche (`TreeBuilder(insert_comments=True)`), le compte d'exécution de
  `<UserId>`, comparé au SID du compte (`sid_du_compte`, `processus_compte.py`),
  l'auteur de `<Author>`, comparé comme aujourd'hui par `_est_le_compte`. Même
  contrat : nom → créée par le compte. Les constantes `_COL_*` disparaissent.
- Échec fermé : une sortie contenant `<!DOCTYPE` ou `<!ENTITY`, ou qui ne se
  parse pas, est une `DroitsAgentRefuses` (le compte écrit le contenu de ses
  tâches, ADR-037). Les règles de suppression, de journalisation d'une tâche non
  supprimable et le drapeau `taches_en_echec` ne changent pas.

## Critères d'acceptation

- [ ] Un test avec une sortie XML inventée (jamais un nom réel) : une tâche du
      compte, une tâche d'un autre compte, une tâche créée par Windows pour le
      compte ; seules les deux premières du compte sont retenues, et la
      dernière se journalise sans bloquer quand sa suppression échoue.
- [ ] Un test : une sortie avec `<!ENTITY` ou illisible lève `DroitsAgentRefuses`
      et lève `taches_en_echec`.
- [ ] Un test : une tâche à plusieurs déclencheurs ne se retire qu'une fois.
- [ ] `pytest` et `mypy` passent.

## Preuve réelle

Sur la machine, sous le compte agent : capturer une vraie sortie
`/query /xml` (fixture à anonymiser avant tout commit), créer une tâche sous le
compte pendant un appel, constater qu'elle est retirée à la clôture, et noter la
durée de `retirer_les_taches` (avant : environ 2,9 s) puis la durée d'ouverture
et de clôture d'un appel entier sur un run de Serpent.

## Ce que ça ne fait pas

- Ne cherche aucune tâche sans lancer une commande sous le compte : le backend
  ne lit ni `TaskCache\Tree` ni `System32\Tasks`.
- Ne change pas ce qui se retire (ADR-088).
