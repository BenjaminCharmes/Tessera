---
agent: codeur
created: 2026-10-23
depends_on: []
estimated_days: 0.5
id: ticket-544
pr_number: 616
priority: high
status: done
title: A backend file can no longer grow past its ceiling
type: test
---

# ticket-544 — Un cliquet sur la longueur des fichiers backend

## Objectif
Qu'aucun fichier Python du backend ne grossisse au-delà de sa taille actuelle,
et qu'aucun nouveau fichier ne dépasse 300 lignes.

## Contexte
`CLAUDE.md` demande des fichiers de moins de 200 lignes, mais rien ne le
vérifie : 22 fichiers de `backend/src` dépassent 300 lignes, dont
`services/git_workspace.py` (2 294) et `services/orchestrator.py` (1 333).
Un gros fichier coûte à chaque agent qui le lit et fait entrer en conflit les
PR d'une même file. KrumIA impose 300 lignes par fichier en CI (revue du
23/10) ; découper tout d'un coup n'est pas réaliste ici, un cliquet l'est.

## Solution proposée
Un test pytest lit tous les `*.py` de `backend/src/tessera` (hors
`__pycache__`) :
- plafond général : 300 lignes ;
- une table `PLAFONDS` (chemin → maximum) liste les fichiers qui dépassent
  aujourd'hui, avec leur taille actuelle comme maximum ;
- le test échoue si un fichier dépasse son plafond, et aussi si un fichier de
  la table est passé sous son maximum sans que la table baisse (le cliquet ne
  remonte pas, et l'écart se resserre à chaque découpage) ;
- le message d'échec nomme le fichier, sa taille et son plafond, et dit
  « découpe le fichier plutôt que de relever le plafond ».

## Critères d'acceptation
- [ ] `backend/tests/test_longueur_des_fichiers.py` existe et définit le plafond général à 300 lignes
- [ ] La table `PLAFONDS` du test liste chaque fichier de `backend/src/tessera` qui dépasse 300 lignes au moment du ticket, avec sa taille exacte
- [ ] Un test vérifie, sur des fichiers temporaires, qu'un fichier hors table de 301 lignes fait échouer le contrôle
- [ ] Un test vérifie, sur des fichiers temporaires, qu'un fichier de la table qui dépasse son maximum fait échouer le contrôle
- [ ] Un test vérifie, sur des fichiers temporaires, qu'un fichier de la table passé sous son maximum fait échouer le contrôle avec un message qui demande de baisser le plafond
- [ ] Le message d'échec contient le chemin du fichier, sa taille et son plafond

## Ce que ça ne fait pas
- Ne découpe aucun fichier (ticket-546 pour `git_workspace.py`).
- Ne touche pas aux tests (`backend/tests`) ni au frontend (ticket-545).