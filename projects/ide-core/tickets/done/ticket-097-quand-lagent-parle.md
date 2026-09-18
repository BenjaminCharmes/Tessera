---
id: ticket-097
title: "Le badge dit quand l'agent parle, et un projet choisit son prompt"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-096]
estimated_days: 1
created: 2026-09-18
---

# ticket-097 — Le badge, et ce qu'il cachait

## Pourquoi

Remarque posée à l'usage, la troisième sur ce sujet : « je comprends vraiment
pas l'intérêt de cette distinction ». Elle était juste, et mes deux réponses
précédentes justifiaient la **protection** — qui est réelle — pas le badge.

Le badge a dit « natif / perso », puis « requis / ajouté ». Dans les deux cas :
**qui a écrit le prompt**. Ça n'apprend rien, puisque c'est toujours un agent,
et ça répond à une question que personne ne se pose devant une liste.

## Ce que ça cachait

Sur dix-sept prompts livrés, **quatre ne sont appelés par rien** :

| Prompt | Pourquoi il ne parle jamais |
|---|---|
| `testeur.md` | L'étape de test lance un sous-processus, sans agent |
| `architect.md` | `ide-core` le déclare ; aucun code ne le charge |
| `orchestrateur.md` | Le nom sert d'étiquette, le prompt n'est jamais lu |
| `doc-updater.md` | Remplacé par ticket-092, désactivé partout |

Le badge les annonçait tous les quatre comme « requis ».

## Et un réglage mort de plus

`AgentConfig.prompt_file` **n'était lu nulle part** — même famille que
`auto_merge_on_approve` (ticket-091), que j'avais manqué au même endroit.
Conséquence immédiate : le projet `carriere` monté au ticket précédent aurait
chargé le prompt générique du codeur, jamais son analyste.

C'est corrigé, et ça donne au passage ce qui manquait pour les projets non-code :
le pipeline appelle toujours les mêmes **étapes** — quelqu'un écrit, quelqu'un
relit — et le projet dit quel **prompt** chaque étape tient.

## Critères d'acceptation

- [x] Le badge dit `pipeline`, `à la demande` ou `jamais appelé`
- [x] Un prompt qu'un `agents.json` branche sur une étape compte comme
      `pipeline`, même si aucun code ne le nomme
- [x] Un test refuse un rôle classé sans prompt livré
- [x] `prompt_file` est honoré, y compris écrit `analyste-carriere.md` sans
      son dossier
- [x] Un `prompt_file` déclaré mais absent **échoue bruyamment** : retomber sur
      le prompt générique produirait du code là où on attend une analyse
- [x] `carriere/agents.json` branche l'analyste sur l'étape du codeur
- [x] Le piège du serveur Vite obsolète est documenté

## Ce que ça ne fait pas

Les quatre prompts jamais appelés ne sont **pas supprimés**. Le badge le dit
maintenant ; c'est une décision à prendre en les voyant, pas à la place de
celui qui les lit.
