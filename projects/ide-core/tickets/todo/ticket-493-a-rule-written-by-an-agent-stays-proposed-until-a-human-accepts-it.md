---
id: ticket-493
title: "A constraint written by an agent stays proposed, and reaches no agent until a human accepts it"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-16
---

# ticket-493 — Une règle écrite par un agent attend l'accord humain

## Objectif

Les règles communes à tous les agents (`memory/contraintes.md`) ne changent
pas sans accord humain, même sur un projet en `autonomy: merge`.

## Contexte

`contraintes.md` part dans chaque appel d'agent, réduit au rôle. Un run qui y
ajoute une ligne et se merge seul change donc la consigne de tous les agents
suivants, sans qu'un humain l'ait lue. C'est arrivé par le chemin normal : le
ticket-463 (architecte) a ajouté l'ADR-053 et ses contraintes dans la PR
#482, mergée sur CI verte.

## Solution proposée

1. **Une section `## Proposées` en tête de `contraintes.md`.** Ce que son
   contenu dit n'est injecté dans **aucun** appel d'agent : le chargeur qui
   réduit le fichier au rôle l'ignore. Le reste du fichier garde son format.
2. **Un run ne peut écrire que là.** Un diff qui modifie `contraintes.md`
   hors de cette section met le run en `blocked` à la fin du tour du codeur,
   avec la raison dans le journal. Le prompt de l'architecte et du codeur le
   dit : une règle nouvelle s'écrit sous `## Proposées`, avec son ADR.
3. **Accepter = déplacer.** Un humain (ou la session ide-core sur son mot)
   déplace la règle dans sa section ; le merge de ce déplacement suit le flux
   normal. Rien d'autre à construire : la page « À toi de jouer » sert déjà à
   poser la question.
4. `decisions.md` n'est pas concerné : il n'est injecté nulle part.

## Ce que ça ne fait pas

- Pas d'interface d'acceptation dans l'IDE : un déplacement de texte suffit.
- N'empêche pas un agent de proposer : c'est le but.

## Critères d'acceptation

- [ ] Un test vérifie que le contenu de `## Proposées` n'apparaît dans le
      contexte d'aucun rôle, et que le reste du fichier y apparaît comme avant
- [ ] Un test vérifie qu'un diff qui ajoute une ligne hors de `## Proposées`
      met le run en `blocked` avec la raison, et qu'un ajout dans la section
      passe
- [ ] Les prompts `architect` et `codeur` disent où écrire une règle nouvelle
- [ ] La règle est ajoutée à `memory/contraintes.md` (Git et périmètre
      d'écriture), et `test_consignes_coherentes.py` passe
