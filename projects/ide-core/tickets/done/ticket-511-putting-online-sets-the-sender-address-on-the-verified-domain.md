---
agent: codeur
created: 2026-10-19
depends_on: []
estimated_days: 0.5
id: ticket-511
pr_number: null
priority: high
status: done
title: Putting a project online sets the e-mail sender address on its verified Resend
  domain
type: fix
---

# ticket-511 — La mise en ligne pose l'adresse d'expéditeur sur le domaine Resend vérifié

## Objectif
Qu'un projet mis en ligne avec la ressource `resend` puisse envoyer des
e-mails réels dès sa mise en ligne, sans variable à ajouter à la main.

## Contexte
La mise en ligne crée le domaine Resend, le fait vérifier et écrit
`RESEND_API_KEY` dans Vercel (`backend/src/tessera/services/provisioning/resend_steps.py`,
`KEY_VARIABLE`). Elle n'écrit jamais d'adresse d'expéditeur. Résultat, le
19/10 sur les deux projets en ligne :
- Kadoomi exige `RESEND_FROM_EMAIL` : sans elle, l'envoi est sauté. Le magic
  link n'arrive jamais, et l'invitation par e-mail affiche « L'e-mail n'a pas
  pu partir pour l'instant ».
- Devinoo retombe sur l'adresse de test de Resend (domaine `resend.dev`),
  qui ne livre qu'au titulaire du compte.

Le bloc `online` sait déjà écrire une variable calculée depuis le domaine
(`derive`, `vercel_steps.py`), mais il faut penser à la déclarer, et aucun
des deux projets ne l'a fait.

## Solution proposée
Quand `resend` fait partie des ressources, la mise en ligne écrit
`RESEND_FROM_EMAIL` si elle est absente de Vercel. Valeur par défaut :
`<Nom> <bonjour@{domain}>`, où `<Nom>` est le nom du projet (`Project.name`,
premier titre du `CLAUDE.md`). Une valeur déclarée dans `online.derive` sous
ce nom l'emporte. La variable n'est jamais réécrite si elle existe déjà. Le
plus simple est de passer par l'étape Variables existante, qui ajoute
`RESEND_FROM_EMAIL` à ses variables voulues quand `resend` est déclaré. Le
dry-run la liste parmi les variables manquantes.

## Critères d'acceptation
- [ ] Un test vérifie que, pour un projet qui déclare la ressource `resend` sans `RESEND_FROM_EMAIL` dans `derive`, l'étape Variables écrit `RESEND_FROM_EMAIL` = `<Nom> <bonjour@<domaine>>`
- [ ] Un test vérifie qu'une valeur déclarée dans `online.derive["RESEND_FROM_EMAIL"]` l'emporte sur la valeur par défaut
- [ ] Un test vérifie qu'une `RESEND_FROM_EMAIL` déjà présente dans Vercel n'est jamais réécrite
- [ ] Un test vérifie qu'un projet sans la ressource `resend` n'écrit pas `RESEND_FROM_EMAIL`
- [ ] L'inspection (dry-run) liste `RESEND_FROM_EMAIL` parmi les variables manquantes quand elle est absente (un test le vérifie)
- [ ] `docs/` décrit la variable posée et comment la surcharger par `derive`

## Dépendances
Aucune.

## Estimation
Une demi-journée.

## Risques
L'adresse n'est pas un secret : elle ne passe pas par le registre des secrets
masqués. Une fois ce ticket actif, Kadoomi et Devinoo ont besoin d'une
nouvelle mise en ligne, que seul Benjamin peut lancer, pour que la variable
soit posée. Leurs replis dans le code (Kadoomi ticket-022, Devinoo
ticket-034) couvrent la période d'ici là.