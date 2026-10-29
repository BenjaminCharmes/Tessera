---
agent: codeur
created: 2026-10-28
depends_on:
- ticket-628
estimated_days: 2
id: ticket-629
pr_number: null
priority: medium
status: done
title: 'Each desk screen shows what its step is really doing: code, reading, tests,
  audit, diff, criteria, verdict'
type: feat
---

# ticket-629 — Des écrans qui montrent l'étape réelle

## Objectif
Qu'un coup d'œil sur l'écran d'un poste dise ce que fait l'agent, et comment
son étape s'est terminée.

## Contexte
Idée de Benjamin du 28/10, validée telle quelle. Aujourd'hui, l'écran d'un poste
(`design/bureau/Ecran.tsx`) est un seul pixel coloré par `TON_ECRAN`, avec une
lueur quand l'agent est actif.

Les données existent :
- l'outil en cours du codeur et du reviewer, via `bulleDOutil` (`lib/bureau/bulleDOutil.ts`) ;
- l'état de chaque poste, via `postesDuRun` (`lib/bureau/postesDuRun.ts`) ;
- les verdicts : `test_result`, `security_audit_done`, `agent_done` du reviewer,
  `validation_done`.

## Solution proposée
L'écran devient une petite scène en pixel art, choisie par le poste et son état :
- **codeur** qui écrit (`Edit`, `Write`, `MultiEdit`) : des lignes de code qui défilent ;
  qui lit (`Read`, `Grep`, `Glob`) : une page fixe ;
- **testeur** occupé : une barre qui avance ;
- **sécurité** occupée : une ligne de balayage ;
- **reviewer** occupé : des lignes de diff, vertes et rouges ;
- **validateur** occupé : une liste de cases ;
- poste **fait** : ✓ ou ✗ selon le verdict de son étape.

Une scène ne s'anime que si la santé du run est `actif`. Un agent silencieux ou
figé garde un écran immobile : l'animation dit qu'il se passe quelque chose, elle
ne doit pas mentir (ADR-058).

## Critères d'acceptation
- [ ] Un test vérifie que l'écran porte `data-ecran` égal à `code`, `lecture`, `tests`, `audit`, `diff` ou `criteres` selon le poste occupé et, pour le codeur, son dernier outil
- [ ] Un test vérifie qu'un poste fait porte `data-ecran="ok"` après un verdict favorable de son étape et `data-ecran="ko"` après un verdict défavorable
- [ ] Un test vérifie que la classe d'animation n'est posée que lorsque la santé du run vaut `actif`
- [ ] Les nouvelles teintes de l'écran n'utilisent que des jetons `--sprite-*` ou les familles d'état d'ADR-026

## Ce que ça ne fait pas
- Ne change pas la taille du poste.
- N'ajoute aucun événement backend.