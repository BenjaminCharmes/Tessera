---
agent: architect
created: 2026-11-19
depends_on: []
estimated_days: 1
id: ticket-1016
pr_number: 1192
priority: high
status: done
title: Decide how to close what the agent account can still keep between runs
type: design
---

## Signalement

- Audit sans contexte du 19/11, constats H3, H4, M2 et L1. Aucun n'est
  prouvé sur le poste : ils demandent une décision de conception et des
  essais, pas un correctif direct.

## Contexte

Après les tickets 1006 à 1009, il reste au compte agent trois moyens de
garder quelque chose d'un run à l'autre :

1. **Un processus sorti du job.** S'il existe une voie pour créer un
   processus hors du job (WMI, service de logon secondaire, BITS) et que ce
   processus réécrit sa propre DACL, `processus_par_sid`
   (`services/providers/processus_compte.py`) le classe illisible et sans
   filiation suspecte : il est ignoré. Il pourrait écrire dans le worktree
   d'un appel suivant ou toucher le `claude.exe` d'un autre appel du même
   compte.
2. **Les caches gardés.** `npm-cache` et le cache de uv survivent au
   nettoyage du profil (ticket-1008). uv ne revérifie pas un paquet déjà
   décompressé.
3. **Les dossiers ouverts à tout utilisateur.** Le compte est membre du
   groupe des utilisateurs : il crée des fichiers dans les dossiers partagés
   de la machine, jamais purgés.

S'y ajoute : les refus d'écriture ne portent que sur les fichiers protégés
qui existent au début du run ; un `CLAUDE.md` ou un `.mcp.json` créé dans un
sous-dossier n'en a pas.

## Ce qu'il faut produire

Une ADR au prochain numéro libre de `memory/decisions.md`, qui tranche pour
chacun des trois points entre : le fermer (et comment), le détecter (et où),
ou l'accepter par écrit. Pistes à comparer : jeton restreint ou niveau
d'intégrité bas pour le compte, cache en lecture seule rempli par le
backend, `UV_LINK_MODE=copy`, refus explicites sur les dossiers partagés,
tout processus illisible né pendant un appel traité comme suspect.

Et les tickets de réalisation qui en découlent, dans `tickets/todo/`.

## Critères d'acceptation

- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` traite les
  trois points, chacun avec sa décision : fermé, détecté ou accepté.
- [ ] Chaque décision « fermé » ou « détecté » a un ticket dans
  `tickets/todo/`, avec `preuve_reelle: true` quand il touche les droits ou
  les processus.
- [ ] L'ADR liste les essais à faire sur le poste avant de coder (sortie du
  job, mode de liaison de uv, DACL d'un processus lancé par le logon
  secondaire).

## Ce que ça ne fait pas

- N'écrit aucun code.