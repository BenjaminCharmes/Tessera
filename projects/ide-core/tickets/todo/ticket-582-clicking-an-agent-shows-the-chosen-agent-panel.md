---
id: ticket-582
title: "Clicking an agent in the office shows the chosen-agent panel"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-581"]
estimated_days: 0.5
created: 2026-10-26
plan: true
---

# ticket-582 — Cliquer un agent ouvre le panneau « Agent choisi »

## Objectif
Que le clic sur un personnage du Bureau serve à quelque chose : voir où en
est cet agent, et ouvrir son fil.

## Contexte
La maquette (`design/maquette/Bureau.dc.html`, colonne de droite) prévoit,
sous « À toi », un panneau « Agent choisi » : rôle, projet et ticket, tour,
dernier signe de vie, ce qu'il fait, modèle, et deux boutons « Suivre le fil »
et « Lui écrire ». Le ticket-566 a livré la colonne « À toi » sans ce panneau,
et le poste de l'agent (`components/BureauView/PosteDeTravail.tsx`) est un
bouton sans action.

## Solution proposée
Le clic sur le poste occupé choisit l'agent ; le panneau s'affiche sous « À
toi » (`components/BureauView/ColonneAToi.tsx` ou un composant voisin) avec
ce que l'état du run fournit déjà (`StreamState`, santé du ticket-549). Une
donnée absente de l'état ne s'invente pas : la ligne ne s'affiche pas
(ADR-058). « Suivre le fil » ouvre le fil du run, comme le bouton « Fil » de
la pièce. Sans agent choisi, le panneau dit « Clique un agent au travail ».
Le tour de plan dit si « Lui écrire » réutilise l'envoi existant (ADR-025) ou
est laissé à plus tard.

## Critères d'acceptation
- [ ] Un clic sur le poste occupé d'une pièce affiche le panneau « Agent choisi » avec le rôle, le projet et le ticket de cet agent ; un test React Testing Library le vérifie
- [ ] Un poste libre n'est pas cliquable (pas de `cursor-pointer`, pas d'action), et un test le vérifie
- [ ] « Suivre le fil » ouvre le même fil que le bouton « Fil » de la pièce, et un test le vérifie avec un double
- [ ] Une donnée absente de l'état du run n'est pas affichée, et un test le vérifie pour le modèle
- [ ] Le diff ne modifie aucun fichier de `backend/`
