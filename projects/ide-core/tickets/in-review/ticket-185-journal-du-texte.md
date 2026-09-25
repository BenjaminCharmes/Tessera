---
id: ticket-185
title: "Le texte d'un run survit à un rechargement de page"
type: feat
status: in-review
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-183"]
estimated_days: 1
created: 2026-09-25
---

## Le problème

Un rechargement de page vide le panneau de ce qu'un agent avait écrit. Le run
continue — ADR-041 l'a découplé exprès — et depuis le ticket-183 le texte
reprend à l'arrivée. Mais ce qui a été dit avant n'est nulle part : `EventHub`
diffuse sans garder, `RunRegistry` ne retient que l'état courant.

C'est vrai d'un F5, d'un onglet fermé, d'une reconnexion après un backend
redémarré — et pas seulement quand quelqu'un travaille sur l'IDE.

## Ce qu'il faut faire

Un journal en mémoire, par run vivant, qui garde les derniers événements de
texte et les rejoue au moment de l'abonnement.

- La rétention se fait à la **publication**, pas dans la file d'un
  observateur : une file saturée jette le texte (`JETABLES`), et le journal
  perdrait exactement ce qu'il existe pour garder.
- Le plafond se compte en **caractères**, pas en événements : un token vaut
  trois lettres, une sortie d'outil quelques milliers.
- `run_closed` oublie le run : sans ça, un backend qui tourne une journée
  garde la trace de tous les runs de la journée.

## Ce que ça ne fait pas

Rien n'est persisté : un backend redémarré repart sans journal, et un run
terminé n'est pas relisible. C'est un tampon de lecture, pas un historique —
celui-ci est dans les commits et les PR.
