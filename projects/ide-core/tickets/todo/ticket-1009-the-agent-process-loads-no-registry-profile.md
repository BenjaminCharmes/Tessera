---
id: ticket-1009
title: "The agent process starts without loading its registry profile"
type: fix
status: todo
priority: medium
agent: codeur
depends_on: [ticket-1008]
preuve_reelle: true
---

## Signalement

- Suite du ticket-998 (ADR-087), constat M3 : `HKCU\…\Command Processor\AutoRun`
  s'exécute à chaque `cmd.exe` lancé par un script npm, d'un appel à l'autre.

## Ce qu'il faut faire

- `services/providers/lanceur_windows.py` : ne plus passer `_LOGON_WITH_PROFILE`
  (flag `0`) à `CreateProcessWithLogonW`. Aucune ruche n'est chargée : `HKCU`
  n'est plus inscriptible par le compte. L'environnement est déjà bâti de zéro
  (ADR-085) et le profil de fichiers vient du ticket-1008.
- **Preuve avant bascule** : le CLI embarqué, node, npm, uv, python et git bash
  doivent démarrer sans ruche. Si l'un échoue, **ne pas contourner** : revenir au
  flag, et `agent-setup-admin.ps1` charge la ruche du compte (`reg load`) pour
  poser un refus d'écriture sur `Software\Microsoft\Command Processor` et
  `Environment`. Dire dans le ticket lequel des deux chemins a été pris.
- Le choix est une constante du lanceur, pas un réglage.

## Critères d'acceptation

- [ ] Le lanceur appelle `CreateProcessWithLogonW` avec `dwLogonFlags = 0` (test sur un faux `adv`).
- [ ] Un test de contrat nomme le flag retiré, pour qu'il ne revienne pas sans décision.
- [ ] `agent doctor` lance `node`, `uv`, `python --version` et le CLI sans ruche.

## Preuve réelle

Sous `AGENT_USER`, faire tenter à un appel `reg add "HKCU\Software\Microsoft\Command Processor" /v AutoRun /d calc` :
constater l'échec d'accès. Lancer ensuite un run complet (CLI, tests, `npm run`) et
constater qu'il aboutit.

## Ce que ça ne fait pas

- Ne vide pas une ruche déjà polluée : un `AutoRun` posé avant ce ticket se supprime
  une fois à la main, administrateur (`reg load` du `NTUSER.DAT` du compte).
