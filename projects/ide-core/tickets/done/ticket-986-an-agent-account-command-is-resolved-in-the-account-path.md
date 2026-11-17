---
agent: codeur
depends_on:
- ticket-982
id: ticket-986
preuve_reelle: true
priority: high
status: done
title: An agent-account command is resolved in the account PATH
type: fix
---

## Contexte

Preuve réelle du 17/11 (Serpent ticket-009, run `a9884f2f`) : le CLI part sous
`tessera-agent`, mais le testeur échoue à chaque tour — « lancement sous
tessera-agent impossible : accès refusé ». Le ticket-982 construit bien le
`PATH` du compte depuis la chaîne d'outils (ADR-086), mais
`CreateProcessWithLogonW` reçoit `npm run typecheck` sans nom d'application :
Windows cherche alors `npm` dans le `PATH` de l'**appelant**, le backend, et y
trouve celui du profil de l'utilisateur, que le compte ne peut pas exécuter.
L'environnement passé au processus ne sert pas à cette recherche.

Reproduit hors run : `node --version` refusé par nom nu, accepté avec le chemin
complet de `C:\ProgramData\Tessera\toolchain\node\node.exe`.

## Ce qu'il faut faire

- `path_compte.resoudre_executable(nom, chemin)` : cherche `nom` dans les
  entrées d'un `PATH` de compte, avec les extensions `.com`, `.exe`, `.bat`,
  `.cmd` ; un fichier sans extension (le script sh `npm`) n'est pas retenu.
- `lancer_sous_compte` remplace le nom nu par ce chemin avant d'appeler le
  lanceur. Introuvable dans le `PATH` du compte : `EchecLancementCompte` qui
  nomme le programme, sans appel au lanceur (ADR-037). Un chemin qui porte un
  dossier passe tel quel.
- Les formes d'`essais_de_commande` (`npm`, puis `npm.cmd`) ne servent plus
  sous le compte : la résolution les remplace.

## Critères d'acceptation

- [x] Test : `node` part avec le chemin de la chaîne d'outils.
- [x] Test : `npm` part en `npm.cmd`, pas avec le script sans extension.
- [x] Test : un nom présent dans le seul `PATH` du backend est refusé, le
      lanceur n'est pas appelé.
- [x] Test : un chemin avec dossier est passé tel quel.

## Preuve réelle

Faite par la session ide-core après merge et redémarrage : Serpent ticket-009
sous `tessera-agent` passe l'étape de test. Avant merge, sur le poste :
`node`, `npm` et `uv --version` rendent leur version sous le compte par nom nu.

## Ce que ça ne fait pas

- Ne met pas `python` sur le `PATH` du compte : uv l'installe sous
  `toolchain\python\cpython-*`, les deux entrées `python` et `python\Scripts`
  de `path_du_compte()` ne contiennent aucun exécutable. Un projet Python
  passe par `uv run`. Le ticket-983 en tient compte.
- Ne change pas le lancement du CLI, déjà appelé par son chemin complet.
