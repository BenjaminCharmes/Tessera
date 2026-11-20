---
agent: codeur
created: 2026-11-13
depends_on: []
id: ticket-963
priority: critical
status: done
title: "A relative Bash target is checked against protected files from the agent's folder too"
type: fix
---

# ticket-963 — Une cible Bash relative est jugée par la protection des fichiers depuis le dossier de l'agent

## Contexte

Audit du lot 941-961 (session Chef, 13/11). Le ticket-959 a fait rattacher
une cible Bash relative au dossier de l'agent dans `hors_perimetre`, mais le
hook passait toujours la cible **brute** à `motif_de_protection`, qui la
rattache à la racine d'écriture. Sous `git_root: ancestor` (ide-core), les
deux contrôles ne jugeaient plus le même fichier :
`echo x > ../../scripts/hooks/pre-push`, `../../scripts/termes_interdits_ci.py`
ou `../voisin/agents.json` passaient le périmètre (dans le dépôt) et
échappaient à la protection (résolus hors du dépôt). L'empreinte ADR-084
aurait vu les scripts, pas le manifeste d'un projet voisin. Actif depuis le
redémarrage du 13/11 au matin.

## Correctif

Le hook calcule une fois le chemin absolu depuis le dossier de l'agent
(`_absolue`) et le donne à `motif_de_protection`. `motif_de_protection`
lui-même ne change pas : `critere_protege` l'appelle avec des chemins de
critère relatifs à la racine, ce qui reste juste.

## Critères d'acceptation

- [x] Un test : depuis `projects/ide-core` sous une racine `ancestor`,
      `../../scripts/hooks/pre-push`, `../../scripts/termes_interdits_ci.py`,
      `../voisin/agents.json` et `cd ../.. && … > scripts/hooks/pre-push`
      sont refusés ; `../../backend/ok.py` passe.
- [x] Les tests existants de la garde d'écriture passent sans changement.

## Ce que ça ne fait pas

- Fait à la main : la faille touche la garde même des agents.
