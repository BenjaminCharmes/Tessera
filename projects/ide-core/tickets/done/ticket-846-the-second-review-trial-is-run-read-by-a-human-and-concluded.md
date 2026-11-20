---
id: ticket-846
title: "The second-review trial is run, read by a human and concluded"
type: chore
status: done
priority: low
agent: codeur
created: 2026-11-05
depends_on: [ticket-842, ticket-844, ticket-845]
estimated_days: 1
pr_number: null
---

# ticket-846 — L'essai est exécuté, relu par un humain, puis conclu

## Objectif

Produire `docs/essais/seconde-revue.md` : les chiffres du rejeu, la relecture, et la
recommandation de la règle d'ADR-079.

## À lire avant de lancer

Ce ticket dépense du quota et attend un humain : **il ne passe ni en file ni en mode
autonome**, une session le conduit à la main (ADR-020). Plafond : 10 $ au total, le bras B
sur Opus étant le seul bras payant. Le candidat est `ollama:qwen3-coder:30b` (déjà installé,
gratuit). Un fournisseur externe et un témoin Claude sont des décisions humaines (spec §7) :
ne les ajouter que sur instruction écrite dans ce ticket.

## Ce qu'il faut faire

1. Lancer le bras B, puis le bras C, par `scripts/seconde_revue.py` du ticket-844, avec
   `--fenetre-caracteres` déduit du contexte du modèle (tokens × 3) et noté dans le rapport.
   Résultats dans `docs/essais/seconde-revue/resultats.jsonl`.
2. Générer la liste des remarques levées (bras, rang, texte, lieu), sans nom de modèle, pour
   la relecture.
3. **Un humain** remplit `docs/essais/seconde-revue/relecture.json` (`confirme`,
   `autre_defaut`, `infonde`). Le codeur ne l'écrit pas et ne le complète pas.
4. Générer le rapport avec `rapport` du ticket-845 et y ajouter à la main : le modèle, la
   fenêtre, les limites vues (taille de l'échantillon, rejeu sans outils), et ce que l'humain
   décide ensuite.

## Critères d'acceptation

- [ ] `docs/essais/seconde-revue/resultats.jsonl` porte une ligne par couple (entrée, bras),
      toutes avec le `gel_sha256` du corpus
- [ ] `docs/essais/seconde-revue/relecture.json` existe, écrit par un humain, avec un
      jugement par remarque levée
- [ ] `docs/essais/seconde-revue.md` existe et porte le bloc de conclusion balisé
- [ ] `backend/tests/test_seconde_revue_rapport.py` relit les trois fichiers et vérifie que la
      décision du bloc est celle de `decision(mesures_depuis(...))`, et que le rapport cite le
      `gel_sha256`
- [ ] Le coût total du rapport est sous 10 $ ; sinon le ticket le dit et s'arrête
- [ ] Aucune ligne de `backend/src`, de `agents.json` ni du pipeline n'est modifiée

## Ce que ça ne fait pas

N'adopte rien. Si la recommandation est `adopter` ou `reserver`, c'est un humain qui ouvre
l'ADR qui amende ADR-009 et ADR-061 et le ticket de branchement ; si elle est `non concluant`,
le rapport dit lequel des deux seuils de validité a échoué.

## Dépendances

tickets 806, 808 et 809.
