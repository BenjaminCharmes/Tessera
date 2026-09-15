---
id: ticket-051
title: "Un system prompt manquant doit échouer bruyamment, pas dégrader"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-050]
estimated_days: 1
created: 2026-09-15
---

# ticket-051 — Échouer bruyamment sur un prompt manquant

## Objectif

Remplacer les replis silencieux sur un system prompt manquant par une erreur
explicite, qui nomme le fichier attendu et la façon de le corriger.

## Contexte

[ticket-050](../done/ticket-050-auth-abonnement-et-prompts.md) a révélé que
`ide_prompts_dir` ne résolvait jamais avec la méthode de lancement documentée.
Le défaut est corrigé, mais **rien n'a signalé la panne pendant tout ce temps** :
cinq services se repliaient chacun sur un prompt générique d'une ligne.

```python
_logger.warning("prompt_file_missing", extra={"path": str(prompt_file)})
return (
    "Tu es un expert en découpage de features en tickets de développement. "
    'Réponds uniquement avec ce JSON : {"tickets": [...], "summary": "..."}'
)
```

Un agent privé de son system prompt ne s'arrête pas : il produit du travail
**hors sujet, mais plausible**. Le codeur ignore les conventions, le reviewer
relit sans critères, le validateur valide au jugé. Ça coûte des tokens, du
temps, et pollue le dépôt de l'utilisateur — nettement plus cher qu'un refus
net. Et ça passe inaperçu : le seul signal est un `WARNING` dans des logs que
personne ne lit.

Cinq sites concernés : `planner`, `project_creator`, `project_analyzer`,
`agent_creator` (fichiers) et `agent_runner` (registre d'agents).

## Solution proposée

1. Une exception `MissingPromptError` et un chargeur partagé, en remplacement
   des cinq implémentations dupliquées de `_load_system_prompt`.
2. Le message nomme le **chemin attendu**, le **rôle** concerné et le réglage
   `IDE_PROMPTS_DIR` — il doit permettre de corriger sans lire le code.
3. Un gestionnaire d'exception FastAPI traduit `MissingPromptError` en réponse
   HTTP dont le `detail` porte ce message, pour qu'il atteigne l'UI au lieu de
   finir en `Internal Server Error`.

## Hors périmètre

Le pipeline d'orchestration continue de dégrader sur d'**autres** absences
(pas de dépôt git, pas de commande de test) : ce sont des dégradations
délibérées et documentées, pas des pannes.

## Critères d'acceptation

- [x] Un prompt manquant lève `MissingPromptError`, jamais un repli silencieux
- [x] Le message nomme le chemin attendu et `IDE_PROMPTS_DIR`
- [x] Les cinq sites passent par le même chargeur
- [x] Un rôle absent du registre d'agents lève la même erreur
- [x] L'API renvoie le message dans `detail`, pas `Internal Server Error`
- [x] Un test par site couvre le cas manquant
- [x] `uv run pytest -q` et `uv run mypy src/` verts

## Dépendances

`ticket-050` (le défaut de chemin doit être corrigé, sinon cette erreur se
déclencherait partout).

## Estimation

**1j**.

## Risques

- **Faible** — le risque est de rendre bloquant un cas aujourd'hui toléré.
  Mitigation : c'est précisément l'objectif, et `ticket-050` garantit que le
  chemin par défaut résout.
