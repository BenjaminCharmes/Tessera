---
agent: codeur
created: 2026-10-27
depends_on:
- ticket-617
id: ticket-618
pr_number: 733
priority: medium
status: done
title: A run that changes an interface captures it from its own worktree
type: feat
---

# ticket-618 — L'étape de capture du pipeline

## Objectif
Après l'approbation du diff et avant la livraison, démarrer l'app du run
depuis son worktree, la capturer, l'arrêter, et le dire. Mode `joindre` d'ADR-062.

## À faire
- Étape appelée seulement si `lire_le_controle` renvoie un mode et que
  `controle_du` est vrai sur les fichiers du diff approuvé. Un seul passage par
  run, jamais à chaque tour de relecture.
- Démarrage : `demarrage.commande` avec `{port}` remplacé par un port libre
  choisi par Tessera, `cwd` = le worktree du run (pas la racine : les services de
  `routers/services.py` partent de la racine, ils montreraient l'ancien code).
  Sans shell, dans le groupe de processus d'ADR-042. Attendre que le port
  réponde (`app_repond`) jusqu'à `delai_s`.
- Captures : `capturer(...)` dans `captures/<projet>/<ticket>/` sous
  `ide_state_dir` ; `dossier_des_captures` prend le ticket en option, la route
  de service lit ce sous-dossier.
- Arrêt : toujours, y compris sur exception ; seulement le processus lancé ici.
  Aucun port occupé n'est tué.
- Journal : une ligne dans `memory/pipeline-log.md` (images, durée de
  démarrage, durée de capture, ou la cause de l'échec) et un événement sur le
  canal du run. Le jeton de session n'apparaît ni dans l'un ni dans l'autre.
- Échec (démarrage, délai, captures manquantes) : journalisé, le run continue.

## Critères d'acceptation
- [ ] Un projet sans `controle_visuel` ne lance ni serveur ni capture (test : aucun processus créé)
- [ ] Un diff sans fichier d'interface ne lance ni serveur ni capture
- [ ] La commande part avec le worktree pour `cwd` et un port libre à la place de `{port}` ; test avec un exécuteur factice
- [ ] Un échec de démarrage ou un délai dépassé journalise la cause, arrête le processus lancé, et le run se termine comme sans l'étape
- [ ] Le processus est arrêté sur exception de l'étape
- [ ] La ligne de journal porte la durée de démarrage et de capture, pour chiffrer le surcoût au fil des runs
- [ ] Le jeton de session ne figure ni dans le journal, ni dans l'événement, ni dans une erreur

## Ce que ça ne fait pas
- Ne juge pas les images ; ne les joint pas à la PR ; n'écrit pas dans le dépôt du projet.
- N'installe pas les dépendances : le `worktree.setup` du projet s'en charge.