---
agent: codeur
depends_on:
- ticket-986
id: ticket-988
preuve_reelle: true
priority: high
status: done
title: Agent-account temporary files and npm cache go to its own profile
type: fix
---

## Contexte

Seconde preuve réelle du 17/11 (Serpent ticket-009, run `02d9b72d`, après le
ticket-986) : les outils démarrent enfin sous `tessera-agent`, mais le testeur
dépasse deux fois son délai. Mesuré ensuite sous le compte, hors run, dans une
copie de Serpent sous `C:\ProgramData\Tessera\worktrees` :

- typecheck, lint et build passent en 3 à 7 s : le compte n'est pas lent en
  soi, les durées du run venaient de la charge du poste à ce moment-là ;
- vitest ne lance **aucun** test : 20 × `EPERM: operation not permitted,
  mkdir 'C:\Users\<utilisateur>\AppData\Local\Temp\…'`. `env_du_compte`
  reprenait `TEMP` et `TMP` du backend, dans le profil de l'utilisateur ;
- `npm ci` échoue en EPERM : le `npmrc` de npm, copié de scoop avec la chaîne
  d'outils (ticket-981), fixe `cache=` dans ce même profil.

Le CLI, lui, recevait déjà `TEMP` et les dossiers du profil de l'agent
(`env_agent._de_base`) : seules les commandes du run (tests, app du contrôle
visuel) partaient avec ceux du backend.

## Ce qu'il faut faire

- `env_agent.env_du_profil(compte)` : `TEMP`, `TMP`, `USERPROFILE`, `HOME`,
  `APPDATA`, `LOCALAPPDATA` dans le profil du compte, et `npm_config_cache`
  dans son `AppData\Local\npm-cache` (une variable d'environnement passe
  devant le `npmrc` intégré). Le CLI et `env_du_compte` s'en servent tous deux.
- `env_du_compte` ne reprend plus `TEMP`/`TMP` du backend ; un `extra` déclaré
  ne remplace aucune de ces variables.
- `npm_config_cache` entre dans les clés permises au CLI : son Bash lance npm.

## Critères d'acceptation

- [x] Test : `env_du_compte` donne `TEMP`, `TMP`, `USERPROFILE` et
      `npm_config_cache` dans le profil de l'agent, aucune valeur sous le
      profil du backend.
- [x] Test : un `extra` ne ramène pas `TEMP` chez l'utilisateur.
- [x] Test : `env_du_profil` et la clé `npm_config_cache` côté CLI.

## Preuve réelle

Avant merge, sur le poste : vitest de Serpent lancé sous `tessera-agent` par
`lancer_sous_compte` avec ce code — aucune EPERM, 178 tests sur 179 passent
(l'échec restant tient aux fins de ligne CRLF de la copie `git archive`, il
passe dans un checkout). Après merge et redémarrage : Serpent ticket-009 sous
`tessera-agent` passe l'étape de test.

## Ce que ça ne fait pas

- Ne réécrit pas le `npmrc` de la chaîne d'outils : `agent setup` le copie
  toujours tel quel ; la variable d'environnement le neutralise. À reprendre
  dans `agent setup` avec le ticket-983.
- Ne fait pas tourner `worktree.setup` sous le compte : la préparation
  (`npm ci`) part toujours sous celui du backend (ADR-085 ne la cite pas).
- Ne change pas le délai du testeur (120 s par défaut) : sur un poste chargé,
  la suite de Serpent peut encore le dépasser ; le ticket-971 relance une fois.
