---
id: ticket-083
title: "Enchaîner la livraison après un run approuvé"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-082]
estimated_days: 2
created: 2026-09-18
---

# ticket-083 — La livraison suit le run

## Pourquoi

Ticket-082 a donné à l'IDE le **droit** d'aller jusqu'au merge. Il n'en avait
toujours pas le **chemin** : pousser demandait un clic, ouvrir la PR un autre,
merger un troisième. Sur un projet qui déclare `merge`, c'est exactement ce
qu'on voulait supprimer.

## Objectif

Enchaîner, après un run approuvé, ce que le projet autorise : rebase sur la
base, PR, attente de CI, merge. Sans jamais forcer, et sans jamais faire
échouer le run.

## Critères d'acceptation

- [x] `LivraisonService` enchaîne les maillons existants et ne décide de rien :
      il lit `autonomy` et s'arrête là où le projet le dit
- [x] Un run **non approuvé** ne se livre pas — son commit porte du travail
      que le reviewer a refusé (ADR-018)
- [x] `rejouer_sur` rebase la branche sur la base ; un conflit **annule** le
      rebase, laisse la branche intacte et nomme les fichiers
- [x] L'attente de CI est bornée : une CI muette rend la main, la PR reste
      ouverte
- [x] Une livraison qui lève ne fait pas échouer le run : le motif remonte
      dans `livraison.arret`
- [x] Un événement `livraison_done` dit à l'écran jusqu'où c'est allé, et
      pourquoi ça s'est arrêté là
- [x] ADR-030 écrite

## Ce que ça ne fait pas

**Résoudre les conflits.** Ils sont détectés, nommés, et le dépôt est laissé
propre — mais trancher un conflit, c'est choisir à la place de l'utilisateur
dans son propre dépôt. Le faire en silence serait la même erreur que merger
sans qu'il l'ait demandé.

La synchronisation issues GitHub → tickets existe (`github-sync`) mais reste
déclenchée à la main : elle n'est pas dans cet enchaînement.
