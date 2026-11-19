---
id: ticket-1018
title: "A new unreadable process during a call blocks the run"
type: feat
status: todo
priority: high
agent: codeur
preuve_reelle: true
---

# ticket-1018 — Un processus illisible né pendant un appel bloque le run

## Objectif

ADR-088, point 1. `processus_par_sid` (`services/providers/processus_compte.py`)
ne soupçonne un processus au jeton illisible que s'il descend du backend ou
d'un processus du compte. Un processus sorti du job n'a plus cette filiation.

## Ce qu'il faut faire

- Prendre, au début de l'appel (`droits_appel.py`), l'inventaire des PID au
  jeton illisible, avec le nom d'image de Toolhelp (lisible même quand
  l'ouverture est refusée).
- À la clôture, tout PID illisible absent de l'inventaire, hors liste blanche
  d'images système fixée par la preuve ci-dessous, lève `ProcessusIllisibles` :
  le run finit `blocked` avec commit (ADR-037), le motif nomme PID et image.
- Un PID réutilisé ne passe pas pour un ancien : l'inventaire garde
  (PID, image) et la filiation de `parentes_processus` reste un signal en plus.

## Critères d'acceptation

- [ ] Un test injecte un processus illisible sans filiation, absent de
  l'inventaire : la clôture lève `ProcessusIllisibles`.
- [ ] Un test injecte un processus illisible présent dans l'inventaire de
  départ, ou d'une image de la liste blanche : rien n'est levé.
- [ ] Un test couvre le PID réutilisé sous une autre image.

## Preuve réelle

À faire sur le poste, hors dépôt (`~/.tessera/worktrees/manuel/`), **avant de
coder** puis après :

1. Sous le compte agent, tenter de créer un processus hors du job : WMI
   (`Win32_Process.Create`), tâche planifiée, BITS. Noter lesquels aboutissent.
2. Pour chacun, lire la DACL du processus créé : l'ouverture en lecture
   limitée est-elle refusée ?
3. Lancer un run complet sans rien d'anormal : relever les processus illisibles
   nés pendant l'appel (candidats de liste blanche). Aucun faux `blocked`.
4. Après le code : rejouer l'étape 1, constater un run `blocked`.

## Ce que ça ne fait pas

- Ne tue pas le processus (sa DACL l'interdit au backend) ; ne ferme aucune
  voie de sortie du job.
