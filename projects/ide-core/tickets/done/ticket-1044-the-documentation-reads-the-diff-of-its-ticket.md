---
agent: codeur
created: 2026-11-23
depends_on: []
estimated_days: 1
id: ticket-1044
pr_number: 1250
priority: high
status: done
title: The documentation pass reads the diff of its ticket, not two months of the
  repository
type: fix
---

# ticket-1044 — La passe de documentation lit le diff de son ticket, pas deux mois de dépôt

## Objectif

Que les agents de documentation reçoivent le diff du ticket qu'ils documentent,
quel que soit l'état des branches locales, et que la liste des fichiers non
montrés ne puisse plus peser plus lourd que le reste du message.

## Contexte

Lu le 23/11 dans les transcriptions des appels de documentation d'ide-core
(runs des tickets 1036 et 1041) : le bloc « Diff livré » du ticket-1041, un
ticket de conception qui ne touche que `memory/` et `tickets/`, commence par
`.claude/commands/new-ticket.md` et le bloc « Fichiers touchés » pèse
130 000 caractères, dont 88 000 pour la seule liste des noms non montrés. Le
message entier fait 230 000 caractères (356 000 le 20/11), et l'agent répond
à côté : « le diff montre des modifications aux skills ».

La chaîne, dans le code :

1. `documenteur_run.py` passe `base=politique.base_branch`. ide-core ne
   déclarait pas `base_branch` : la valeur est `None`, alors que le run, lui,
   part de `base_du_projet(politique)` (`controle_base.py`), qui retombe sur
   le réglage global.
2. `_reference` (`services/git_workspace/ticket_diff.py`), sans base, prend
   la branche courante si ce n'est pas celle du ticket, sinon `main`. Pendant
   le run, la branche courante **est** celle du ticket : la référence est le
   `main` local. Sur ce PC il date du 28 septembre, 1 150 commits derrière
   `develop`. Le diff `main...branche` est donc tout ce que le dépôt a reçu
   depuis. Le commentaire de `_reference` décrit ce piège sans le fermer.
3. `bloc_fichiers` (`documentation_code.py`) borne le contenu des fichiers
   (`_BORNE_FICHIERS`) mais écrit sans borne les noms de
   `fichiers_non_montres`.

C'est la cause première des passes à « 0 fichier(s) » sur ide-core : les agents
documentent un diff qui n'est pas celui du ticket. Les projets qui déclarent
`base_branch` ne sont pas touchés. La déclaration est ajoutée à la main à
`projects/ide-core/agents.json` par la PR de cette fiche ; ce ticket ferme le
piège dans le code, pour tout projet qui ne déclare rien.

## Solution proposée

- `documenteur_run.py` passe la base réelle du run :
  `base_du_projet(politique)`.
- `_reference` : sans base explicite, et sur la branche du ticket, la
  référence est la base par défaut des réglages (locale, sinon `origin/`),
  jamais un `main` codé en dur.
- `bloc_fichiers` : au-delà d'un nombre borné de noms (valeur de départ : 30),
  la liste dit combien d'autres fichiers ne sont pas montrés, sans les nommer.

## Critères d'acceptation

- [ ] Un test de `documenteur` sur un projet sans `base_branch` vérifie que
      la base transmise au service est celle de `base_du_projet`.
- [ ] Un test de `diff_du_ticket`, dans un dépôt où `main` est en retard sur
      la base par défaut et où la branche courante est celle du ticket, sans
      base explicite : le diff ne contient que le commit du ticket.
- [ ] Un test de `bloc_fichiers` avec 200 fichiers non montrés : le bloc
      nomme au plus 30 fichiers et donne le nombre des autres.
- [ ] Le diff ne modifie pas `backend/src/tessera/routers/tickets.py`.

## Ce que ça ne fait pas

- Ne retire pas des appels sans outils les consignes du projet que le CLI
  charge (45 000 caractères par appel sur ide-core) : à mesurer à part.
- Ne rattrape pas les tickets comptés comme documentés à tort.
- Ne met pas à jour le `main` local du poste.

## Vérification après merge (session ide-core, hors critères)

Dans la transcription du premier appel de documentation suivant : le bloc
« Diff livré » ne nomme que les fichiers du ticket.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

`_reference` sert aussi à l'écran du diff d'un ticket (`routers/tickets.py`) :
son comportement avec une base explicite ne doit pas changer.