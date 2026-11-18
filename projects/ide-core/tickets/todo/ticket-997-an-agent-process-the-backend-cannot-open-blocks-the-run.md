---
id: ticket-997
title: "An agent process the backend cannot inspect blocks the run"
type: fix
status: todo
priority: high
agent: codeur
depends_on: []
preuve_reelle: true
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

- Distinguer « jeton d'un autre compte » de « jeton illisible ». Un processus
  au jeton illisible n'est suspect que s'il descend d'un processus de l'appel :
  sa chaîne de parents (`CreateToolhelp32Snapshot`, `th32ParentProcessID`,
  lisible sans ouvrir le processus) remonte au backend ou à un processus du
  compte déjà vu pendant l'appel. Un processus du compte qu'on ne peut pas
  arrêter met le run en `blocked` (ADR-037).
- Agrandir le tampon d'`EnumProcesses` tant qu'il est plein.
- `taskkill` qui échoue parce que le PID n'existe plus : succès, journalisé.

## Refus du 18/11 (PR #1157, non mergée)

Le premier passage tenait pour suspect **tout** processus apparu depuis le
début de l'appel dont `OpenProcess` est refusé. Mesuré le 18/11 sur le poste,
sans droits d'administrateur : 187 processus sur 533 refusent l'ouverture
(System, services, csrss, winlogon, dwm, services de pilotes), et **3
nouveaux en 3 minutes**, machine au repos. Un appel d'agent dure plusieurs
minutes : presque chaque run aurait fini `blocked` à tort.

Pistes écartées, vérifiées sur le poste :
- `WTSEnumerateProcessesW` ne rend le SID d'aucun de ces 187 processus à un
  non-administrateur.
- La session ne suffit pas seule : 180 sont en session 0, mais 7 sont dans
  la session de l'utilisateur (csrss, winlogon, dwm, services de pilotes).

Vérifié le 18/11 : un processus lancé par `CreateProcessWithLogonW` a pour
parent Toolhelp le processus appelant (le backend), pas le service seclogon.

La branche `ticket-997-…` porte le premier passage : en garder le tampon
agrandi et le `taskkill` sur PID disparu ; refaire la règle du suspect.

## Critères d'acceptation

- [ ] Test : processus du compte au jeton illisible, descendant d'un
  processus de l'appel → `DroitsAgentRefuses`.
- [ ] Test : processus au jeton illisible apparu pendant l'appel, dont la
  chaîne de parents ne passe ni par le backend ni par un processus du compte
  (un service, parent `services.exe`) → ignoré, aucune erreur.
- [ ] Test : tampon plein → seconde énumération plus grande.
- [ ] Test : PID disparu avant `taskkill` → pas d'erreur.

## Ce que ça ne fait pas

- N'empêche pas la sortie du job elle-même : c'est l'objet d'une conception
  à part si ce ménage ne suffit pas (`JOB_OBJECT_LIMIT_BREAKAWAY_OK` est déjà
  absent).
