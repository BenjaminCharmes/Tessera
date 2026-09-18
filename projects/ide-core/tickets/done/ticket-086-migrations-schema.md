---
id: ticket-086
title: "Le schéma SQLite évolue sans perdre l'historique"
type: chore
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-085]
estimated_days: 1
created: 2026-09-18
---

# ticket-086 — Des migrations pour la base

## Pourquoi

`init_db` faisait des `CREATE TABLE IF NOT EXISTS` et rien d'autre. Il créait
ce qui manquait, et ignorait tout le reste.

Conséquence : ajouter une colonne un jour ne l'aurait **jamais** fait arriver
dans une base existante. Sans erreur, sans message. Le code aurait lu une
colonne que la base n'a pas, et l'échec serait apparu à l'usage.

L'historique des runs et des coûts n'est pas reconstructible : il ne se recrée
pas, il se migre.

## Critères d'acceptation

- [x] `PRAGMA user_version` porte le numéro de schéma de la base
- [x] `_MIGRATIONS` liste les évolutions dans l'ordre ; seules celles en
      retard s'appliquent
- [x] Rejouer `init_db` ne rejoue pas une migration déjà passée
- [x] Les données survivent à une migration
- [x] Une base plus récente que le code est laissée intacte, avec un
      avertissement — le cas d'un aller-retour entre deux machines
- [x] Un test vérifie qu'une base neuve et une base migrée ont le **même**
      schéma : c'est ce qui interdit de modifier `_CREATE_TABLES`

## Ce que ça ne fait pas

Pas de migration descendante. Revenir en arrière sur un schéma demande de
décider quoi faire des données que l'ancienne version ne sait pas porter —
ça se traite au cas par cas, pas par un mécanisme générique.
