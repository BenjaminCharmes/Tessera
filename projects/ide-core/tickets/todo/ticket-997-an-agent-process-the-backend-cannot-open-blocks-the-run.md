---
id: ticket-997
title: "An agent process the backend cannot inspect blocks the run"
type: fix
status: todo
priority: high
agent: codeur
depends_on: []
---

## Signalement

- Audit sans contexte du 17/11, constat H2 (HIGH), plus L7.

## Contexte

`services/providers/processus_compte.py` (ticket-991) ignore un processus dont
`OpenProcess` ou `OpenProcessToken` échoue. Un processus de l'agent sorti du
job (WMI `Win32_Process.Create`, tâche planifiée à son nom) et qui a réécrit
la DACL de son processus n'est alors ni listé ni tué : il survit à l'appel.
`droits_appel.clore_appel` ne fait le ménage que si aucun autre appel n'est
en cours.

L7 : `EnumProcesses` est tronqué en silence au-delà de 16 384 PID ; un
processus qui se termine entre l'énumération et `taskkill` fait échouer le
ménage et met le run en `blocked` à tort.

## Ce qu'il faut faire

- Distinguer « jeton d'un autre compte » de « jeton illisible » : pour un
  processus dont le jeton ne s'ouvre pas, lire son SID autrement s'il le faut
  (ou traiter l'illisible comme suspect quand le processus a été créé après
  le début de l'appel) ; un processus du compte qu'on ne peut pas arrêter met
  le run en `blocked` (ADR-037).
- Agrandir le tampon d'`EnumProcesses` tant qu'il est plein.
- `taskkill` qui échoue parce que le PID n'existe plus : succès, journalisé.

## Critères d'acceptation

- [ ] Test : processus du compte au jeton illisible → `DroitsAgentRefuses`.
- [ ] Test : tampon plein → seconde énumération plus grande.
- [ ] Test : PID disparu avant `taskkill` → pas d'erreur.

## Ce que ça ne fait pas

- N'empêche pas la sortie du job elle-même : c'est l'objet d'une conception
  à part si ce ménage ne suffit pas (`JOB_OBJECT_LIMIT_BREAKAWAY_OK` est déjà
  absent).
