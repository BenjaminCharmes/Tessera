---
name: radar-hebdo
description: Use when the « radar hebdo » ritual is due, or when asked to turn Vigie's weekly radar into tickets — reads each project's radar export, checks every candidate against the repository, and writes only the tickets that still make sense, without launching any queue.
---

# Radar hebdomadaire : des candidats aux tickets

Vigie écrit chaque dimanche soir ce que la veille propose à chaque projet. Un
candidat n'est pas un ticket : le 16/11, le radar proposait à un projet une
montée de version déjà en ligne. Ce skill **confronte chaque candidat au
dépôt** avant d'écrire quoi que ce soit.

## Avant de commencer

- Les exports sont des fichiers de ce PC, ignorés par git :
  `projects/vigie/exports/radar-<projet>.md` (tickets candidats, dépendances
  à surveiller, retards d'une version majeure) et
  `projects/vigie/exports/veille/<semaine>.json` (les autres onglets de la
  veille).
- Lire la date « écrit le » de chaque export. Un export de plus de huit jours
  n'est pas le radar de la semaine : le dire, ne pas le traiter.
- Pas de `git` dans le checkout d'un projet dont une file tourne.

## 1. Confronter chaque candidat au dépôt

Pour chaque « ticket candidat » d'un `radar-<projet>.md`, lire dans le dépôt
du projet, sur sa branche de base à jour (`git fetch`, puis lire
`origin/<base_branch>`) :

- **la version installée** (verrou de dépendances, pas le manifeste) : une
  montée déjà faite s'écarte ;
- **les tickets existants** (`tickets/todo/`, `in-progress/`, `done/`) : un
  ticket qui couvre déjà le sujet s'écarte ;
- **chaque critère proposé** : un fichier, un champ ou un test qu'il nomme
  existe-t-il vraiment sous ce nom ? Un critère faux bloque un run trois
  tours de suite. Le corriger ou le retirer.

Les « dépendances à surveiller » et les retards d'une version majeure ne
deviennent un ticket que s'il y a une raison de sécurité ou de fin de support
citée dans l'export. Sinon ils restent dans le récapitulatif.

Pour un projet sans radar de dépendances, `veille/<semaine>.json` peut
suggérer une idée de fonctionnalité : au plus **une** par projet et par
semaine, et seulement si elle sert un objectif écrit dans son `CLAUDE.md`.

## 2. Écrire les tickets retenus

- Suivre le skill `new-ticket` ; le numéro vient de
  `scripts/prochain_numero.py ticket --projet projects/<projet>`.
- La fiche cite sa source : la semaine du radar et le lien de la version ou
  de l'article.
- Une PR par projet, vers sa branche de base, qui ne contient que les fiches.
  La merger quand ses contrôles sont verts.
- **Ne lancer aucune file** : la session du projet, ou Benjamin, décide du
  moment.

## 3. Rendre compte

Un récapitulatif par projet : candidats retenus (numéro de ticket), candidats
écartés **avec leur raison**, exports absents ou périmés. Prévenir la session
de chaque projet qui reçoit des tickets. Ce qui demande une décision (argent,
changement de version majeure, abandon d'une dépendance) va sur la page « À
toi de jouer », pas dans un ticket.

## Ce que ce skill ne fait pas

- Il ne modifie pas Vigie ni ses exports.
- Il n'écrit rien pour un projet `"confidentiality": "professional"`.
- Il ne monte aucune dépendance lui-même.
