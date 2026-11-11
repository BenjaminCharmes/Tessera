---
id: ticket-931
title: "The Bash write guard expands ~ and variables, and refuses a relative target after a directory change it cannot follow"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-11
---

# ticket-931 — La garde d'écriture Bash développe `~` et les variables, et refuse une cible relative après un `cd` qu'elle ne suit pas

## Objectif

Qu'une redirection vers `~/.bashrc`, `$HOME/…` ou un fichier relatif après un
`cd` hors du projet ne passe plus pour une écriture dans le projet.

## Contexte

Audit du 11/11, vérifié sur `origin/develop` :

- **`~` et `$VAR` ne sont pas développés.** `hors_perimetre`
  (`backend/src/tessera/services/providers/perimetre.py`, l. 68-92) fait
  `Path(chemin)` puis, si le chemin n'est pas absolu, `racine / chemin` :
  `~/.bashrc` devient `<racine>/~/.bashrc`, dans le périmètre. `echo x >> ~/.bashrc`
  et `echo x > $HOME/.bashrc` passent. `garde_jetons.py` développe déjà
  (`_resoudre`, `os.path.expanduser(os.path.expandvars(…))`), et la leçon du
  ticket-879 le demande pour toute protection de chemin.
  `motif_de_protection`
  (`backend/src/tessera/services/providers/chemins_proteges.py`) a le même
  angle mort.
- **`cd` absolu ou illisible.** Le ticket-925 (#1035) a ajouté
  `_dossier_de_tete`
  (`backend/src/tessera/services/providers/redirections_bash.py`,
  l. 182-196) : un `cd x &&` relatif et lisible en tête préfixe les cibles.
  Un `cd` absolu (`/…`, `X:`), illisible (`$`, `` ` ``, `cd -`) ou suivi d'un
  second changement de dossier rend `None`, et la cible reste relative à la
  racine : `cd /c/Users && echo x > f` passe. Le test
  `test_unreadable_cd_keeps_current_behaviour` de
  `backend/tests/test_redirections_heredoc_cd.py` fige ce comportement.

ADR-031 : la garde lexicale attrape une erreur, pas une évasion
(`python - <<E … E` passe toujours). Ce ticket la fait échouer fermée sur des
formes qu'elle lit déjà, sans promettre plus.

## Solution proposée

- Avant `hors_perimetre` et `motif_de_protection`, chaque cible passe par
  `os.path.expanduser(os.path.expandvars(…))`, et la forme Git Bash `/c/…`
  est ramenée à `C:/…` sous Windows, comme dans `garde_jetons.py` (factoriser
  si possible). Une cible qui garde un `$` ou commence encore par `~` après
  développement est refusée.
- Un `cd`/`pushd` absolu lisible se suit comme un relatif : les cibles
  relatives suivantes en sont préfixées, puis jugées par `hors_perimetre`.
  Plusieurs `cd` lisibles successifs se composent.
- Après un changement de dossier qui ne se suit pas avec certitude
  (variable non développable, `cd -`, `popd`, sous-shell), une cible
  **relative** est refusée, avec un message qui demande un chemin absolu.
- Les cas acceptés du ticket-925 (`cd backend/tests && echo x > ../app/y.py`)
  restent acceptés.

## Critères d'acceptation

- [ ] Un test du hook de `backend/src/tessera/services/providers/perimetre.py`
      vérifie que `echo x >> ~/.bashrc` est refusé.
- [ ] Un test vérifie que `echo x > $HOME/.bashrc` est refusé, `HOME` pointant
      vers un dossier temporaire hors du projet.
- [ ] Un test vérifie que `cd <dossier absolu hors du projet> && echo x > f`
      est refusé.
- [ ] Un test vérifie que `cd <chemin absolu du projet>/backend && echo x > f`
      est accepté.
- [ ] Un test vérifie que `cd "$X" && echo x > y` est refusé quand `X` n'est
      pas défini.
- [ ] `test_unreadable_cd_keeps_current_behaviour` de
      `backend/tests/test_redirections_heredoc_cd.py` est remplacé par un test
      du nouveau comportement.

## Ce que ça ne fait pas

- Ne voit pas les écritures hors des formes simples (`sed -i`, `dd of=`,
  interpréteur sans `-c`) : ticket-933 pour les fichiers protégés.
- Ne développe pas comme le shell de l'agent sous `AGENT_USER` : `~` y désigne
  un autre dossier personnel, hors du projet dans les deux cas, donc refusé.

## Dépendances

Aucune. Le ticket-930 touche `_NOMS_PROTEGES_INLINE` dans le même module,
loin des fonctions modifiées ici.

## Estimation

Un jour.

## Risques

Faux refus d'un agent qui enchaîne `cd "$VAR" && … > fichier` légitimement :
le message lui dit d'écrire un chemin absolu. `redirections_bash.py` fait
267 lignes : extraire le suivi du `cd` dans un module voisin s'il dépasse 300.
