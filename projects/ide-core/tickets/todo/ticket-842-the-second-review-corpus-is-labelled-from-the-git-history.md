---
id: ticket-842
title: "The second-review corpus is labelled from the git history"
type: chore
status: todo
priority: low
agent: codeur
created: 2026-11-05
depends_on: [ticket-841]
estimated_days: 1
pr_number: null
---

# ticket-842 — Le corpus de l'essai est étiqueté depuis l'historique git

## Objectif

Un fichier `docs/essais/seconde-revue/corpus.json`, figé, de runs passés approuvés et mergés :
au moins 10 diffs défectueux et 10 diffs sains (ADR-079).

## Contexte

L'étiquetage ne se fait que par l'historique, jamais après avoir vu une sortie de modèle
(spec §2). Sources de `defaut` : le ticket-733 (résolution de conflit qui effaçait une
fonctionnalité), les constats de `docs/audit/securite.md` et `docs/audit/regles.md` portant
sur du code déjà approuvé, et les commits `fix:` de `develop` qui corrigent un ticket mergé
(`git log` et `git show`, lecture seule). Sources de `sain` : tickets mergés sans correction
ni constat dans les sept jours suivants, de tailles variées. Le ticket-750 (faux positif de
l'audit sécurité) n'est pas un défaut du reviewer : il est hors corpus.

## Ce qu'il faut faire

1. Relever les candidats, noter pour chacun le `sha` du squash et la preuve (SHA de
   correction, ticket, ou constat d'audit avec son numéro).
2. Écrire `fichiers_defaut` et `defaut` (une phrase) pour chaque `defaut` ; calculer `sensible`
   avec `est_sensible` du ticket-841 sur les fichiers du diff.
3. Viser au moins 4 `defaut` sensibles : si l'historique n'en donne pas, le dire dans le
   fichier et dans le ticket, ne pas inventer de défaut.
4. Calculer `gel_sha256` avec `somme_gel` et l'écrire.

## Critères d'acceptation

- [ ] `docs/essais/seconde-revue/corpus.json` existe et `charger_corpus` le lit sans erreur
- [ ] `verifier_taille` rend `[]` : 10 `defaut`, 10 `sain`, 4 `defaut` sensibles au moins ;
      sinon le ticket reste en `blocked` avec le compte réel
- [ ] `shas_manquants` rend `[]` sur ce dépôt ; la sortie est citée dans la PR
- [ ] `backend/tests/test_seconde_revue_corpus_reel.py` charge le vrai fichier et vérifie
      `verifier_taille == []` et la somme de gel ; il ne teste pas l'existence des SHA, qu'un
      clone superficiel ne porte pas
- [ ] Aucun nom de client, e-mail ou jeton dans le fichier (ADR-043)

## Ce que ça ne fait pas

N'appelle aucun modèle. Ne corrige aucun des défauts listés.

## Dépendances

ticket-841.
