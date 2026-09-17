---
id: ticket-075
title: "Montrer le run au centre, et rendre le diff lisible"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-074]
estimated_days: 1
created: 2026-09-17
---

# ticket-075 — Le run au centre, et un diff lisible

## Le run

Pendant un run, le centre affichait le tableau des tickets — ou, si on avait
demandé le diff, « ce ticket n'a jamais été lancé », puisque la branche n'existe
pas encore. La seule fenêtre sur le travail en cours était une colonne de 320
pixels, où le flux d'un agent défile dans un cadre de quelques lignes.

C'est pourtant le moment où l'on a le plus besoin de place : ce que chaque
agent lit, écrit et conclut est ce qui permet de décider s'il faut intervenir
ou arrêter.

Le centre montre donc le run — tour, agent qui parle, avancement de la file,
blocs d'agents en grand, verdict — et la colonne de droite garde ce qui sert à
**agir** : répondre, infléchir, arrêter. Un fichier ou un diff ouvert
explicitement garde la priorité : c'est une demande de l'utilisateur.

La liste des agents est **dérivée des événements**, pas écrite à la main :
`AgentRole` ne couvre pas toutes les étapes, et une liste figée afficherait des
blocs vides pour des agents qui n'ont pas tourné.

## Le diff

Le premier jet versait tout le diff dans Monaco : cinq fichiers concaténés,
ajouts et retraits de la même couleur, aucune navigation. Sur un run qui touche
deux Markdown de plusieurs centaines de lignes, on ne lit rien.

Le diff est désormais découpé par fichier — avec ses compteurs `+`/`-` — et on
n'en affiche **qu'un à la fois**. Chaque ligne est peinte selon son rôle :
ajout, retrait, en-tête de section, contexte. Le découpage vit dans `parse.ts`,
testé à part : l'affichage se contente de peindre.

## Vérifié

897 tests backend, mypy sur 65 fichiers, 351 tests frontend, 5 flows E2E,
`npm run build`.
