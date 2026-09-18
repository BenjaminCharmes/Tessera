---
id: ticket-094
title: "Ce qui est protégé est ce dont le produit dépend"
type: fix
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-093]
estimated_days: 1
created: 2026-09-18
---

# ticket-094 — « natif » ne voulait rien dire

## Pourquoi

Question posée à l'usage, et elle est juste : **c'est toujours un agent qui
écrit les prompts.** Celui que l'IDE livre et celui qu'on crée depuis le chat
sortent du même endroit, et ce sera toujours le cas. Distinguer « natif » de
« perso », c'est distinguer sur l'origine — une information qui n'apprend rien
et ne prédit rien.

La vraie ligne de partage est ailleurs : **le code charge-t-il ce prompt par
son nom ?**

- `codeur.md` est chargé par son nom. Le supprimer casse le pipeline au
  prochain run.
- Un `expert-sql.md` que personne ne nomme peut disparaître sans rien casser.

C'est ça que la protection défend, et ce n'est pas ce que le badge disait.

## Critères d'acceptation

- [x] Un test **dérive** l'ensemble protégé du code : tout prompt chargé par
      son nom dans `src/` doit être déclaré protégé
- [x] Le badge dit « requis » / « ajouté », plus « natif » / « perso »
- [x] Son infobulle dit la conséquence : « le supprimer casserait les runs »

## Ce que ça change vraiment

La panne de ticket-079 — `agent-creator` supprimé d'un clic parce que la liste
écrite à la main avait dérivé du code — recommencerait à l'identique pour un
agent ajouté plus tard. Elle ne le peut plus : la liste est confrontée au code
à chaque exécution de la suite.
