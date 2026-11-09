---
id: ticket-889
title: "A fixed token leaves no stale session token file behind"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-11-09
---

# ticket-889 — Un jeton fixe ne laisse aucun fichier de session périmé derrière lui

## Objectif

Qu'un backend démarré avec `STATIC_TOKEN` ne laisse pas sur le disque un
`jeton-de-session` d'un démarrage précédent, que le lanceur affiche et que les
sessions de projet lisent pour recevoir 401.

## Contexte

Le 09/11, Benjamin a passé Tessera au jeton fixe (`STATIC_TOKEN` dans le coffre).
Le backend précédent avait été arrêté par `tessera.ps1 stop`, qui tue le
processus : `jeton_de_session.arreter()` n'a pas tourné et le fichier de 08:48
est resté. Au redémarrage, `jeton_de_session.demarrer()` voit `settings.static_token`
et ne touche pas au fichier. Conséquences vues le même matin : `tessera.ps1 run`
a affiché `#jeton=<ancien>`, et les sessions Affût et Kadoomi ont lu ce fichier et
reçu 401 sur toute l'API.

`backend/src/tessera/services/noyau/jeton_de_session.py` porte `demarrer()`
et `arreter()` ; le lanceur lit le fichier dans `scripts/tessera.ps1`, sans
pouvoir savoir qu'un jeton fixe est dans le coffre.

## Solution proposée

Dans `demarrer()`, quand `settings.static_token` est renseigné, supprimer le
fichier `chemin_du_fichier()` s'il existe (`unlink(missing_ok=True)`), avant de
retourner. Le lanceur, qui n'affiche la ligne `#jeton=` que si le fichier existe,
n'a pas à changer. Un fichier d'un démarrage antérieur sans jeton fixe est
périmé de toute façon : le jeton tiré vivait en mémoire du processus mort.

## Critères d'acceptation

- [ ] `jeton_de_session.demarrer()` supprime `chemin_du_fichier()` quand
      `settings.static_token` est renseigné.
- [ ] Un test écrit un fichier périmé sous un `ide_state_dir` temporaire, appelle
      `demarrer()` avec un `static_token`, et constate que le fichier n'existe plus
      et que `courant()` vaut le jeton fixe.
- [ ] Un test vérifie que `demarrer()` sans `static_token` écrit toujours le
      jeton tiré dans le fichier (comportement du ticket-878 conservé).
- [ ] Le docstring du module dit qu'un jeton fixe efface le fichier d'un
      démarrage précédent.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Aucun : le fichier supprimé ne vaut plus rien dès que le processus qui l'a
écrit est mort.

## Ce que ça ne fait pas

- Ne copie jamais `STATIC_TOKEN` sur le disque.
- Ne change pas `tessera.ps1`.
