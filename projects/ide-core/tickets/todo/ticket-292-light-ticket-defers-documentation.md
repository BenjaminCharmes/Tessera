---
id: ticket-292
title: "A ticket declared light defers its documentation to the next batch"
type: feat
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: ["ticket-288"]
estimated_days: 1
created: 2026-10-01
---

# ticket-292 — Un ticket léger reporte sa documentation au lot suivant

## Objectif

Qu'un petit ticket, déclaré comme tel, ne paye pas une passe de
documentation complète, sans perdre sa trace dans la doc.

## Contexte

Après chaque run approuvé, `_documenter_le_run`
(`services/orchestrator.py:487-548`) lance `doc-technique` puis
`doc-fonctionnelle` sur les tickets livrés depuis le dernier marqueur
(ADR-035). Pour un renommage ou un test de plus, ces deux appels coûtent
plus que le changement lui-même.

Ce qui **ne** s'allège **pas** : la sécurité et le validateur. Ce sont des
portes qui échouent fermées (ADR-039), et un ticket peut être écrit par un
agent ou importé d'une issue GitHub. Une déclaration qui ouvrirait une porte
deviendrait une façon de la contourner. Sur un petit diff, elles sont déjà
rapides : le temps fixe se trouve dans la documentation et la CI.

## Solution proposée

- `Ticket` gagne un champ `light: bool = False`, lu dans le frontmatter
  comme `plan`. Valeur absente ou non booléenne : `False`.
- Un run approuvé d'un ticket `light` saute `_documenter_le_run` et n'avance
  pas le marqueur. Le prochain run non léger documente le lot entier, ticket
  léger compris, puisque le lot part du marqueur.
- Le skill `new-ticket` cite le champ. La mise à jour du skill est manuelle :
  un agent ne peut pas écrire dans `.claude/`.

## Critères d'acceptation

- [ ] Un test vérifie qu'un frontmatter `light: true` donne
      `ticket.light == True`, et qu'une valeur absente ou invalide donne
      `False`
- [ ] Un test vérifie qu'un run approuvé d'un ticket léger n'appelle pas le
      documenteur et n'émet pas `documentation_started`
- [ ] Un test vérifie qu'un ticket léger lance quand même l'audit sécurité
      et le validateur
- [ ] Un test vérifie que le run non léger qui suit documente aussi le
      ticket léger

## Ce que ça ne fait pas

- Les modèles des agents ne changent pas : un petit diff est déjà jugé vite.
- La CI ne s'allège pas : c'est le ticket-291.
- Une file qui se termine sur des tickets légers les laisse sans
  documentation jusqu'au prochain ticket normal.

## Dépendances

ticket-288 : si la documentation coûte moins d'une minute, ce ticket ne vaut
pas son champ de plus, et il se ferme en `cancelled`.

## Estimation

1 jour.

## Risques

Un ticket marqué léger par erreur ne perd rien : sa documentation part au
lot suivant.
