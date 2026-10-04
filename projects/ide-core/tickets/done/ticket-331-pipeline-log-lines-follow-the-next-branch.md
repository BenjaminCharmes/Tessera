---
id: ticket-331
title: "Pipeline log lines written after delivery follow the next run onto its branch, instead of being stranded on the delivered one"
type: fix
status: done
pr_number: 246
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-04
---

# ticket-331 — Les lignes de journal écrites après la livraison suivent le run suivant

## Objectif

Que les lignes du journal écrites après le push d'une livraison (rebase, PR
ouverte, confiée au CIWatcher) arrivent sur `develop`, au lieu de mourir sur
une branche locale jamais poussée.

## Contexte

Constaté le 2026-10-04 en faisant le ménage des branches locales : sur 14
tickets (306 à 330), les trois ou quatre lignes de livraison de chacun
n'existent que dans un commit `chore: tessera pipeline bookkeeping` de la
branche locale du ticket, **postérieur** à la tête de sa PR. Elles ne sont
jamais arrivées sur `develop` ; la 317 a dû les rattraper à la main (#243).

La chaîne :

1. La livraison pousse la branche et ouvre la PR (`_noter_et_pousser`,
   ticket-270) ; ce n'est qu'ensuite que l'orchestrateur journalise les
   étapes de livraison, puis la file « confiée au CIWatcher ».
2. Ces lignes restent non commitées dans l'arbre (ticket-301 les tolère).
3. Le run suivant, avant de changer de branche, appelle
   `commit_bookkeeping` (ticket-314) : il les commite **sur la branche du
   ticket précédent**, déjà poussée, souvent déjà mergée par squash. Ce
   commit n'est jamais poussé.

Le risque que le ticket-303 avait noté (« le run suivant les commitera ») se
réalise donc, mais sur la mauvaise branche.

## Solution proposée

Dans l'étape de création de branche, avant `commit_bookkeeping` : relever
les lignes ajoutées au journal depuis `HEAD` et remettre le fichier dans
l'état de `HEAD`. Après le changement de branche, réécrire ces lignes à la
fin du journal de la nouvelle branche, sans dupliquer une ligne déjà
présente. Le run les commite alors avec sa propre tenue de livres, et elles
arrivent sur `develop` avec sa PR.

Les fichiers de ticket en attente gardent le comportement du ticket-314.
Si le changement de branche échoue, les lignes sont réécrites quand même :
aucune n'est perdue.

## Critères d'acceptation

- [x] Un test sur un dépôt git temporaire vérifie que des lignes de journal
      en attente sur la branche d'un ticket précédent se retrouvent dans le
      journal de la nouvelle branche
- [x] Le même test vérifie que la branche précédente ne reçoit aucun commit
      portant ces lignes
- [x] Un test vérifie qu'une ligne déjà présente dans le journal de la
      nouvelle branche n'est pas dupliquée
- [x] Un test vérifie que les lignes sont réécrites quand la création de la
      branche échoue
- [x] Un test vérifie qu'un fichier de ticket en attente est toujours commité
      avant le changement de branche (ticket-314)

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Les lignes réécrites se placent après celles de la nouvelle branche au moment
du changement : l'ordre chronologique du fichier peut s'inverser de quelques
lignes. Le pilote de fusion `union` du journal (#217) gère les conflits.
