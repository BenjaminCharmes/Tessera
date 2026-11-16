---
agent: codeur
created: '2026-11-16'
depends_on: []
id: ticket-979
priority: high
status: done
title: Les processus des agents n'écrivent pas de bytecode Python
type: fix
---

## Contexte

ide-core, run `d65cecd7`, 16/11 à 10:46 UTC. Le codeur du ticket-977 lance
les tests qu'il a touchés, et certains d'entre eux (`test_hook_pre_push.py`,
`test_hook_pre_push_projet.py`…) importent `scripts/hooks/pre-push`. Python
crée alors `scripts/hooks/__pycache__/pre-pushcpython-311.pyc`. L'empreinte
des fichiers protégés (`pipeline_empreinte.py`, ADR-084) couvre tout
`scripts/hooks/` : elle voit un fichier apparaître pendant l'appel et met le
run en `blocked`. Le tour d'un ticket approuvé par l'audit et le validateur
est perdu sur un faux positif.

Exclure `__pycache__` de l'empreinte serait une faille. Python charge un
`.pyc` de `__pycache__` à la place de sa source quand l'en-tête (date et
taille de la source) correspond. Un `.pyc` fabriqué par un agent
s'exécuterait donc au prochain `git push` à la place du hook relu. Le
fichier doit rester surveillé ; ce sont les agents qui ne doivent pas le
produire.

## Ce qu'il faut faire

- `env_du_sous_processus` (`services/providers/env_sdk.py`) pose
  `PYTHONDONTWRITEBYTECODE=1` : tout Python lancé par le CLI d'un agent
  (`Bash`, tests du skill de vérification) n'écrit plus de bytecode.
- L'étape de test du pipeline (`TestRunner._lancer`,
  `services/verification/test_runner.py`, qui passe par
  `env_du_code_de_projet` ou `lancer_sous_compte`) reçoit la même variable.
- Le compte agent (`env_de_l_agent`, `env_agent.py`, liste fermée des clés
  admises) la reçoit aussi.
- L'empreinte ne change pas : un `.pyc` qui apparaît sous un dossier protégé
  reste un motif d'arrêt.

## Critères d'acceptation

- [ ] Test : `env_du_sous_processus(...)["PYTHONDONTWRITEBYTECODE"] == "1"`.
- [ ] Test : l'environnement de l'étape de test porte la variable.
- [ ] Test : l'environnement du compte agent porte la variable.
- [ ] Test : `pipeline_empreinte` voit toujours un fichier apparaître sous
      `scripts/hooks/__pycache__/` (le test existant ou un nouveau, avec un
      dossier temporaire).

## Ce que ça ne fait pas

- Ne supprime pas les `__pycache__` déjà présents dans les checkouts.
- Ne couvre pas un agent qui écrit délibérément un `.pyc` : c'est
  l'empreinte qui l'arrête, comme aujourd'hui.