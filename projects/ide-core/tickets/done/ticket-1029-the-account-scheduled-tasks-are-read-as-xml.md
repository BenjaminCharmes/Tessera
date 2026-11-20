---
agent: codeur
depends_on: []
id: ticket-1029
pr_number: 1221
preuve_reelle: true
priority: medium
status: done
title: The account scheduled tasks are read as XML
type: refactor
---

# ticket-1029 — Les tâches planifiées du compte se lisent en XML

## Objectif

Remplacer la lecture `schtasks /query /fo csv /nh /v` (2,0 s sous le compte) par
`/query /xml` (0,2 s, mesure du 20/11), sans rien retirer de la fermeture du
ticket-1018.

## Essai du 20/11

Une tâche créée sous le compte (`schtasks /create`), puis `schtasks /query
/xml` sous le compte : la sortie **n'est pas un document XML**. Elle ouvre
`<Tasks>`, puis répète pour chaque tâche un commentaire `<!-- \nom -->`, une
déclaration `<?xml version="1.0" encoding="UTF-16"?>` et un élément `<Task>`
(espace de noms `http://schemas.microsoft.com/windows/2004/02/mit/task`) :
202 déclarations dans la sortie du poste. Un analyseur XML à qui l'on donne
toute la sortie la refuse. Pour la tâche du compte, `<URI>` porte son nom,
`<UserId>` le SID du compte et `<Author>` la forme `poste\compte`.

## À faire

**`taches_compte.py`**

- `_supprimer_les_taches` lance `schtasks /query /xml` ; les arguments restent
  fixés dans le module.
- `taches_du_compte` découpe la sortie en tâches sur les déclarations
  `<?xml`, puis analyse chaque `<Task>…</Task>` séparément
  (`xml.etree.ElementTree`). Le nom vient de `<URI>` ; à défaut, du
  commentaire qui précède la déclaration. Le compte d'exécution vient de
  `<UserId>` : la tâche est celle du compte si la valeur est son SID
  (`sid_du_compte`, `processus_compte.py`) **ou** son nom (`_est_le_compte`).
  L'auteur vient de `<Author>`, comparé par `_est_le_compte`. Même contrat
  qu'aujourd'hui : nom → créée par le compte. Les constantes `_COL_*`
  disparaissent.
- Échec fermé (ADR-037, le compte écrit le contenu de ses tâches) : un
  fragment contenant `<!DOCTYPE` ou `<!ENTITY`, un fragment qui ne s'analyse
  pas, ou une sortie qui porte des déclarations `<?xml` sans qu'aucune tâche
  ne soit lue, est une `DroitsAgentRefuses`. Les règles de suppression, de
  journalisation d'une tâche non supprimable et le drapeau `taches_en_echec`
  ne changent pas.

## Critères d'acceptation

- [ ] Un test avec une sortie inventée (jamais un nom réel), de la forme
      réelle — `<Tasks>` puis, par tâche, commentaire, déclaration `<?xml` et
      `<Task>` — portant trois tâches : A s'exécute sous le compte et il en
      est l'auteur ; B s'exécute sous un autre compte ; C s'exécute sous le
      compte, créée par un autre auteur. `taches_du_compte` rend A (créée par
      le compte) et C (non créée par le compte), et pas B.
- [ ] Un test : un `<UserId>` donné par nom (`poste\compte`) est reconnu comme
      un `<UserId>` donné par SID.
- [ ] Un test : la suppression refusée de C se journalise sans lever ; celle
      de A lève `DroitsAgentRefuses`.
- [ ] Un test : un fragment avec `<!ENTITY`, ou qui ne s'analyse pas, lève
      `DroitsAgentRefuses` et lève `taches_en_echec`.
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