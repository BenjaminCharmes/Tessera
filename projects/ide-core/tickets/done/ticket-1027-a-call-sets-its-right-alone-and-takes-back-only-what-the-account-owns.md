---
agent: codeur
depends_on: []
id: ticket-1027
pr_number: 1219
preuve_reelle: true
priority: high
status: done
title: A call sets its right alone and takes back only what the account owns
type: refactor
---

# ticket-1027 — Un appel pose son droit seul et ne reprend que ce que le compte possède

## Objectif

Réaliser l'ADR-091 sur le worktree : ouverture et clôture d'un appel sous le
compte agent en quelques secondes. Le droit d'écriture du compte se pose à
l'ouverture d'un appel et se retire à sa clôture (celle du dernier appel qui se
chevauchent sur la même racine, comme aujourd'hui) ; aucun droit ne dure d'un
appel à l'autre.

## À faire

**`droits_worktree.py`**

- `poser_ecriture` ne pose plus que `/grant` du compte `(OI)(CI)M` sur la racine.
- Nouvelle `poser_base(racine, backend)` : contrôle total du backend, puis
  `OWNER_RIGHTS`, puis `_proteger_git` (l'ordre actuel de `poser_ecriture`,
  preuve du 19/11). Idempotente. Mémorisée par `(chemin résolu, st_ctime_ns de
  la racine)` : un worktree recréé au même chemin repasse par la base. Aucune
  de ces ACE ne donne un droit au compte (`.git` : lecture seule, comme après
  la clôture actuelle).
- `retirer_ecriture` : `/remove:g` du compte sur la racine d'abord (le droit est
  retiré même si la suite échoue), puis la reprise ciblée. Plus de
  `/setowner /T` ni de `/reset /T`, plus de `_proteger_git` à la clôture.
- `accorder_droits_agent` appelle `poser_base` puis pose les refus ; `_REFUSES`
  ne sert plus qu'à reposer le refus d'un fichier protégé que la reprise a remis
  à l'héritage (un fichier du compte, run `blocked` de toute façon, ADR-088).

**`droits_appel.py`** : `ouvrir_appel` (et `_poser_ou_retirer`) appelle
`poser_base` si la racine n'est pas mémorisée. L'ordre de `_clore_sous_verrou`
ne change pas : processus restants arrêtés, puis retrait du droit — rien ne
tourne plus sous le compte pendant la reprise.

**Nouveau `reprise_ciblee.py`** (domaine `providers`, sous 300 lignes)

- `Protocol SecuriteFichiers` : `lire(chemin) -> InfoSecurite(proprietaire_sid,
  dacl_protegee)` et `reprendre(chemin, backend_sid)`. Les tests s'y branchent
  avec un faux ; l'implémentation réelle est en `ctypes` (pas de `pywin32`,
  ADR-083), tests réels ignorés hors Windows.
- `reprendre_arbre(racine, compte, backend, securite, ignorer)` : parcours par
  `os.scandir`, attributs lus sans suivre les liens, en `asyncio.to_thread`.
  Reprise (propriétaire rendu au backend, DACL remise à l'héritage) de toute
  entrée dont le propriétaire est le compte ou dont la DACL est protégée ; les
  autres ne sont pas touchées. La `.git` de la racine est ignorée (le compte n'y
  a que la lecture). Après reprise, relecture de chaque entrée reprise :
  propriétaire backend et DACL non protégée, sinon `DroitsAgentRefuses`.
- Un lien (jonction ou lien symbolique) n'est jamais suivi ni parcouru : son
  attribut de point d'analyse se lit dans le `scandir`, sa sécurité s'ouvre par
  un handle `FILE_FLAG_OPEN_REPARSE_POINT` (jamais par un chemin qui résout la
  cible). Un lien du compte reçoit seulement le changement de propriétaire ; un
  lien à DACL protégée est une `DroitsAgentRefuses`.
- Entrée disparue entre le parcours et l'ouverture : ignorée. Entrée qui ne se
  lit pas ou ne se reprend pas : `DroitsAgentRefuses` nommant le chemin, sans
  contenu (run `blocked`, ADR-037).

## Critères d'acceptation

- [ ] `poser_ecriture` ne lance qu'un `/grant` ; `poser_base` pose le reste une
      fois par racine, et se repose sur un worktree recréé au même chemin.
- [ ] `retirer_ecriture` ne lance ni `/setowner` ni `/reset` ; le `/remove:g`
      précède la reprise, et reste posé en cas d'échec de celle-ci.
- [ ] Un test avec faux `SecuriteFichiers` : une entrée du compte, une entrée à
      DACL protégée sont reprises ; une entrée du backend ne l'est pas.
- [ ] Un test : un lien du compte n'est jamais parcouru ; son changement de
      propriétaire passe par le handle ; un lien protégé lève.
- [ ] Un test : une entrée illisible lève `DroitsAgentRefuses` ; le run sort
      `blocked`.
- [ ] Les refus de `_REFUSES` ne sont plus posés qu'une fois par run, sauf pour
      un fichier repris.
- [ ] `pytest` et `mypy` passent ; aucune configuration de test ne change.

## Preuve réelle

Sur la machine, sous le compte agent, sur un run de Serpent (`node_modules`
inclus) : noter la durée d'ouverture (`ouvrir_appel`) et de clôture
(`clore_appel`), et la comparer aux 4,8 s et 22,8 s du 20/11. Constater, après
la clôture, qu'aucune entrée du worktree n'appartient au compte et qu'aucune
DACL ne le nomme (hors `.git`, lecture seule) ; qu'un fichier protégé garde son
refus ; qu'une jonction créée par le compte est retirée de son propriétaire sans
que sa cible ait changé. Refaire la mesure après un `npm ci` sous le compte
(attendu : environ 4 s de reprise).

## Ce que ça ne fait pas

- Ne garde aucun droit du compte entre deux appels.
- Ne touche ni profil ni tâches : tickets 1028 et 1029.