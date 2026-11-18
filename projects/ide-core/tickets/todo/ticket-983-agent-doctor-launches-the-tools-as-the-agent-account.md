---
id: ticket-983
preuve_reelle: true
title: "agent doctor launches node, uv and python as the agent account"
type: fix
status: todo
priority: high
agent: codeur
depends_on: [ticket-981, ticket-982]
---

## Contexte

ADR-086. `tessera.ps1 agent doctor` dit « node trouvé sur ce poste » avec
`Get-Command`, sous le compte de l'utilisateur : il a laissé passer l'EPERM de
Serpent ticket-009.

## Ce qu'il faut faire

- Un module Python `tessera.agent_doctor_cli` (lancé par `python -m` depuis
  le venv, comme `coffre_cli`) : par `lancer_sous_compte` et `path_du_compte()`,
  il exécute `node --version`, `uv --version` et `uv run --no-project python
  --version` (aucun `python.exe` n'est sur le `PATH` du compte, ticket-986) sous
  `AGENT_USER`, avec un délai borné, et imprime une ligne par outil. Code de
  sortie non nul au premier échec ; le message nomme la cause (logon, EPERM,
  introuvable). Aucun secret imprimé.
- `Invoke-AgentDoctor` remplace les `Get-Command` de `uv` et `node` par cet
  appel ; un échec indique `agent setup`.
- Le doctor vérifie aussi qu'aucun droit de `tessera-agent` ne subsiste sur le
  profil de l'utilisateur.
- Le module lance aussi `npm config get cache` sous le compte : une valeur
  hors du profil de l'agent est un échec (ticket-988 : le `npmrc` intégré à
  npm, copié de scoop, vise le profil de l'utilisateur).
- `agent-setup.ps1` vide le `npmrc` intégré de la copie
  (`toolchain\node\node_modules\npm\npmrc`) après avoir copié node : ni
  `prefix=` ni `cache=` sous `C:\Users`.
- Un agent n'exécute pas ce module : il lit le coffre (contrainte
  « secret de Tessera »), le garde de commande le refuse.

## Refus du 18/11 (PR #1172, non mergée)

Le premier passage, approuvé par le pipeline, a été exécuté en vrai sous
`tessera-agent` le 18/11. Trois défauts, invisibles avec un lanceur factice :

1. **Dossier de lancement** : `main()` lance chaque outil dans `Path.cwd()`,
   c'est-à-dire `backend/` du checkout (`tessera.ps1` fait `Push-Location
   backend`). `lancer_sous_compte` → `ouvrir_appel` y cherche la racine git et
   tombe sur le dépôt Tessera. Depuis le ticket-999, la garde refuse : trace
   Python `DroitsAgentRefuses: …\tessera n'est pas sous le dossier des
   worktrees`. Sans le 999, le doctor aurait donné au compte agent le droit
   d'écrire sur tout le dépôt Tessera. Lancer les outils depuis un dossier
   **hors de tout dépôt git**, où `ouvrir_appel` ne pose rien (par exemple
   `C:\ProgramData\Tessera\toolchain`).
2. **Python hors de la chaîne** : `uv run --no-project python --version` est
   lancé sans les variables de `chaine_python.env_du_setup`. Sous le compte,
   uv ne voit pas `C:\ProgramData\Tessera\toolchain\python` et **télécharge
   Python 3.14.6 depuis Internet** dans le profil de l'agent (relevé `uv -v`).
   Passer `UV_PYTHON_INSTALL_DIR`, `UV_PYTHON_PREFERENCE=only-managed` et
   `UV_PYTHON_DOWNLOADS=never` : une chaîne absente doit échouer, pas se
   télécharger. Depuis un dossier qui porte un `pyproject.toml`, la même
   commande sortait en code 2.
3. **Exception non attrapée** : `_verifier` n'attrape que
   `EchecLancementCompte` et `OSError`. `DroitsAgentRefuses` (et toute autre
   exception du lancement) doit devenir une ligne d'échec, jamais une trace.

## Critères d'acceptation

- [ ] Test : les outils se lancent dans un dossier hors dépôt git ; lancé
      depuis le checkout, `ouvrir_appel` ne reçoit jamais la racine du dépôt.
- [ ] Test : la commande Python reçoit `UV_PYTHON_INSTALL_DIR` (la chaîne
      partagée), `UV_PYTHON_PREFERENCE=only-managed` et
      `UV_PYTHON_DOWNLOADS=never`.
- [ ] Test : un `DroitsAgentRefuses` levé au lancement donne une ligne
      d'échec et le code 1, sans trace.
- [ ] Test du module avec un lanceur factice : succès, échec d'un outil,
      délai dépassé, mot de passe absent.
- [ ] Test : le module est refusé à un agent par le garde Bash.
- [ ] Test : un cache npm rendu sous le profil de l'utilisateur est un échec
      qui nomme `agent setup`.
- [ ] Test : `agent-setup.ps1` réécrit le `npmrc` de la copie de node.

## Preuve réelle

Faite par la session ide-core après merge et redémarrage, pas par le
validateur : avec la chaîne de ticket-981, `agent doctor` passe ; en
renommant `toolchain\node`, il échoue en nommant node. Puis Serpent
ticket-009 sous `tessera-agent` passe l'étape de test.

## Ce que ça ne fait pas

- Ne répare rien : il constate et renvoie à `agent setup`.
