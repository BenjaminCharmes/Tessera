---
agent: codeur
depends_on:
- ticket-981
- ticket-982
id: ticket-983
preuve_reelle: true
priority: high
status: blocked
title: agent doctor launches node, uv and python as the agent account
type: fix
---

## Contexte

ADR-086. `tessera.ps1 agent doctor` dit « node trouvé sur ce poste » avec
`Get-Command`, sous le compte de l'utilisateur : il a laissé passer l'EPERM de
Serpent ticket-009.

## Ce qu'il faut faire

- Un module Python `tessera.agent_doctor_cli` (lancé par `python -m` depuis
  le venv, comme `coffre_cli`) : par `lancer_sous_compte` et `path_du_compte()`,
  il exécute `node --version`, `uv --version` et `python --version` sous
  `AGENT_USER`, avec un délai borné, et imprime une ligne par outil. Code de
  sortie non nul au premier échec ; le message nomme la cause (logon, EPERM,
  introuvable). Aucun secret imprimé.
- `Invoke-AgentDoctor` remplace les `Get-Command` de `uv` et `node` par cet
  appel ; un échec indique `agent setup`.
- Le doctor vérifie aussi qu'aucun droit de `tessera-agent` ne subsiste sur le
  profil de l'utilisateur.
- Un agent n'exécute pas ce module : il lit le coffre (contrainte
  « secret de Tessera »), le garde de commande le refuse.

## Critères d'acceptation

- [ ] Test du module avec un lanceur factice : succès, échec d'un outil,
      délai dépassé, mot de passe absent.
- [ ] Test : le module est refusé à un agent par le garde Bash.

## Preuve réelle

Faite par la session ide-core après merge et redémarrage, pas par le
validateur : avec la chaîne de ticket-981, `agent doctor` passe ; en
renommant `toolchain\node`, il échoue en nommant node. Puis Serpent
ticket-009 sous `tessera-agent` passe l'étape de test.

## Ce que ça ne fait pas

- Ne répare rien : il constate et renvoie à `agent setup`.