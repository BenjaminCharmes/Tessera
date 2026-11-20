---
agent: architect
created: 2026-11-19
depends_on: []
estimated_days: 1
id: ticket-1025
pr_number: null
priority: high
status: done
title: 'Design: a call under the agent account costs a few seconds, the right still
  lasts one call'
type: design
---

# ticket-1025 — Conception : un appel sous le compte agent coûte quelques secondes, le droit dure toujours un appel

## Objectif

Écrire l'ADR et les tickets de réalisation qui ramènent l'ouverture et la
clôture d'un appel sous le compte agent sous 15 secondes, **sans allonger la
durée du droit** : il se pose à l'ouverture d'un appel et se retire à sa
clôture (ADR-083, ADR-087).

## Contrainte fixée par l'utilisateur le 19/11

Un premier run de ce ticket a proposé un droit qui dure tout le run, avec une
clôture légère entre deux appels. Refusé trois fois à la revue : un processus
du compte resté vivant écrirait dans le worktree entre deux appels.
L'utilisateur a tranché : **le droit reste par appel**, le gain se cherche
dans la façon de le poser et de le retirer. Une voie « par run » n'est pas à
proposer ; elle ne serait rouverte par l'utilisateur que si un appel ne
passait pas sous 15 secondes.

## Mesures du 20/11, sur le poste, hors run

Worktree de Serpent (9 248 entrées avec `node_modules`), sous le compte agent.

Coût actuel d'un appel ordinaire, environ 29 s :

| Étape (`droits_appel.py`) | Durée |
|---|---|
| ouverture : `poser_ecriture` (trois `/grant` propagés, puis `.git`) | 4,8 s |
| clôture : `retirer_les_taches` | 2,9 s |
| clôture : `reinitialiser_profil` | 3,9 à 5,6 s |
| clôture : `retirer_ecriture` (`/setowner /T` puis `/reset /T`) | 16,0 s |

Les mesures du 19/11 donnaient 58 s pour les mêmes étapes : la durée varie du
simple au double d'un jour à l'autre, l'ordre de grandeur des écarts ci-dessous
ne change pas.

Essais d'un prototype, même worktree :

| Essai | Durée |
|---|---|
| ouverture : le seul `/grant` du compte sur la racine, le contrôle total du backend et `OWNER RIGHTS` restant posés | 0,9 à 1,6 s |
| clôture : `/remove:g` du compte sur la racine | 1,0 à 1,7 s |
| clôture : parcours qui lit propriétaire et drapeau « DACL protégée » de chaque entrée, et ne reprend (propriétaire rendu au backend, DACL remise à l'héritage) que les entrées du compte ou protégées — appel ordinaire, 3 entrées reprises sur 9 248 | 0,6 s |
| le même parcours après `npm ci` sous le compte, 9 157 entrées reprises | 4,2 s |
| lecture des propriétaires du profil (1 697 entrées) | 0,1 s |
| `schtasks /query /xml` sous le compte | 0,2 s |
| `schtasks /query /fo csv /nh /v` sous le compte (forme actuelle) | 2,0 s |

Après la reprise ciblée, aucune entrée n'appartient au compte et sa DACL ne le
nomme plus. La sortie `/xml` porte, pour chaque tâche, un commentaire avec son
nom, `<UserId>` (un SID) et `<Author>`.

Voies essayées et fermées : le backend, non administrateur, ne peut ouvrir ni
la clé `TaskCache\Tree` du registre ni le dossier `System32\Tasks` ; il ne voit
donc pas une tâche du compte sans lancer une commande sous le compte.

Limites du prototype, à traiter par l'ADR : il utilisait `pywin32`
(`GetNamedSecurityInfo`, `SetNamedSecurityInfo`), alors qu'ADR-083 demande
`ctypes` ; il ouvrait un lien par son chemin, donc sa cible ; le `.git` de la
racine, dont l'héritage est coupé et que le backend ne contrôle pas
entièrement, doit garder sa règle propre (`_proteger_git`) ; le profil n'a été
que mesuré, pas prototypé.

## Pistes à comparer

- **Reprise ciblée du worktree** : ne reprendre que ce dont le compte est
  propriétaire ou dont la DACL est protégée, au lieu de `/setowner /T` et
  `/reset /T` sur tout l'arbre.
- **Un seul droit qui bascule** : le contrôle total du backend et
  `OWNER RIGHTS` posés une fois au début du run (`accorder_droits_agent`) ;
  seul le `/grant` du compte se pose et se retire à chaque appel.
- **Tâches planifiées lues en XML** au lieu de la forme détaillée.
- **Reprise ciblée du profil**, sur le même principe que le worktree.
- Ne rien changer.

## Ce qu'il faut produire

- Une ADR au prochain numéro libre de `memory/decisions.md`, qui retient une
  voie, donne la durée attendue d'un appel et dit ce qu'elle laisse ouvert.
- Les tickets de réalisation dans `tickets/todo/`, numérotés par
  `scripts/prochain_numero.py`.

## Critères d'acceptation

- [ ] Une ADR au prochain numéro libre de `projects/ide-core/memory/decisions.md`
  compare au moins trois des pistes ci-dessus, avec leurs durées mesurées, et
  en retient une.
- [ ] L'ADR dit explicitement que le droit d'écriture du compte se pose à
  l'ouverture d'un appel et se retire à sa clôture, et ne propose aucun droit
  qui dure d'un appel à l'autre.
- [ ] L'ADR dit pourquoi une entrée dont le compte n'est pas propriétaire n'a
  pas besoin d'être reprise, et ce qui arrive quand une entrée ne peut être ni
  lue ni reprise (`DroitsAgentRefuses`, run `blocked`, ADR-037).
- [ ] L'ADR dit comment un lien (jonction, lien symbolique) est traité sans
  être suivi, et ce que deviennent les refus posés sur les fichiers protégés
  (`_REFUSES` de `droits_worktree.py`) quand la racine n'est plus remise à
  zéro.
- [ ] Chaque ticket de réalisation de `projects/ide-core/tickets/todo/` porte
  `preuve_reelle: true`, nomme les fonctions de `droits_worktree.py`,
  `profil_agent.py` ou `taches_compte.py` qu'il change, et demande de noter la
  durée d'ouverture et de clôture mesurée sur un run de Serpent.
- [ ] Aucun fichier hors de `projects/ide-core/tickets/` et
  `projects/ide-core/memory/` n'est modifié.

## Ce que ça ne fait pas

- N'écrit aucun code.
- Ne retire aucune des fermetures des tickets 1006, 1008, 1014, 1015 et 1018
  sans le dire dans l'ADR.
- Ne change pas la durée du droit du compte.