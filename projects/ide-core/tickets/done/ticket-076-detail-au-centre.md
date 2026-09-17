---
id: ticket-076
title: "Un détail au centre pour les onglets qui n'en avaient pas"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-075]
estimated_days: 2
created: 2026-09-17
---

# ticket-076 — Agents, coûts, markdown, et deux pannes trouvées en route

## Le principe

Le rail dit **quoi**, le centre montre **le détail**. C'était déjà vrai pour
Tickets et Fichiers ; ça ne l'était pas pour Agents ni Coûts, qui entassaient
tout dans une colonne de 280 pixels pendant que le centre restait vide.

## Agents

Le **prompt système** — la définition entière d'un agent, ce qui détermine tout
son comportement — n'était visible nulle part : la liste n'en montrait qu'un
extrait, en infobulle au survol. Quand un agent se comporte mal, c'est pourtant
la première chose à lire, et il fallait ouvrir `agents/prompts/*.md` dans
VSCode. Le backend l'exposait déjà ; il manquait l'écran.

## Coûts

Le panneau donnait le total, les runs et la dépense par ticket. Manquait la
ventilation qui permet d'agir : **par agent**, parce qu'elle dit qui consomme,
et **par modèle**, pour préparer l'arbitrage du jour où l'on descend un agent en
Haiku. La donnée était là depuis toujours, dans `agent_calls`.

Les parts sont en pourcentage : sur quelques centimes, un montant absolu ne dit
rien, une part se lit tout de suite.

## Markdown rendu

Tickets, ADR, `CLAUDE.md`, prompts d'agents : tout est du Markdown, et le lire
avec ses `##` et ses `**` demande un effort que le contenu ne justifie pas. Une
bascule **Rendu / Source** apparaît sur les fichiers `.md` et sur les prompts.

**Le HTML est assaini.** Ces fichiers sont écrits par des agents : rendre leur
HTML tel quel donnerait à un texte généré le pouvoir d'exécuter du script dans
une application qui a accès au système de fichiers. `marked` et `DOMPurify`
étaient présents en dépendances **transitives** — elles sont maintenant
déclarées, sinon elles pouvaient disparaître au prochain verrouillage.

## Deux pannes trouvées en route

**Un agent se supprimait sans confirmation.** Un clic sur la croix effaçait le
prompt du disque. C'est arrivé pour de vrai pendant cette session :
`agent-creator` a disparu, et n'a pu être restauré que parce qu'il est versionné
avec le dépôt. Un agent créé depuis l'IDE, lui, aurait été perdu. Une
confirmation explicite est désormais requise.

**Un run restait « en cours » pour toujours.** `finish_run` n'était appelé que
sur le chemin nominal, et, placé dans un `finally`, il disparaissait dès que la
socket mourait : la tâche était annulée et l'`await` ne se terminait jamais. Le
run est maintenant clos **avant** toute écriture réseau, et émettre vers une
socket morte ne tue plus le run — il continue côté serveur, ce que l'interface
annonce déjà.

## Vérifié

903 tests backend, mypy sur 65 fichiers, 365 tests frontend, 5 flows E2E,
`npm run build`.
