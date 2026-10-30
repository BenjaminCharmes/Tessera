---
id: ticket-724
title: "The documentation batch also keeps AGENTS.md and the project description current"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-708"]
plan: true
estimated_days: 1
created: 2026-10-30
---

# ticket-724 — La documentation par lot tient aussi `AGENTS.md` et la description du projet à jour

## Objectif
Quand un projet change, sa documentation par lot met à jour tout ce qui le décrit :
`README.md`, `docs/`, `CLAUDE.md`, mais aussi `AGENTS.md` et la description
affichée dans Tessera.

## Contexte
Demande de Benjamin le 30/10. Une revue à la main des 17 projets l'a montré :
plusieurs `CLAUDE.md` disaient encore « squelette posé, rien de fonctionnel » alors
que dix tickets étaient livrés, et les descriptions affichées dans Tessera
dataient de la création des projets.

`_DOCUMENTABLE` (`backend/src/tessera/services/documentation.py`) couvre
`README.md` et `docs/`. `CLAUDE.md` n'est édité que par doc-technique, et
seulement quand le projet déclare `pipeline.doc_claude_md`
(`backend/src/tessera/services/documentation_claude_md.py`). `AGENTS.md` n'est
jamais fourni. La description affichée vient de la clé `description` d'`agents.json`
(ticket-399, `project_loader.py`, `_chaine_declaree`) : aucun agent ne peut écrire ce
fichier (ADR-027), et c'est voulu.

## Solution proposée
1. `AGENTS.md`, quand il existe à la racine de la documentation, est fourni et
   éditable par doc-technique, aux mêmes conditions que `CLAUDE.md`
   (`pipeline.doc_claude_md`).
2. doc-technique peut rendre, dans sa sortie, une `description` (une ou deux
   phrases, 220 caractères au plus, sans retour à la ligne). Le **service** de
   documentation, et non l'agent, la remplace dans `agents.json` : il ne touche
   que cette clé et laisse le reste du fichier octet pour octet. Une description
   trop longue, multiligne ou sans preuve (règle « preuve » d'ADR-057) est
   refusée et journalisée, sans bloquer le reste du lot.
3. Le prompt `agents/prompts/doc-technique.md` dit quand proposer une
   description : quand le lot change ce que fait le produit.
4. Une règle sous `## Proposées` de `memory/contraintes.md`, avec une ADR au
   prochain numéro libre de `memory/decisions.md` : « le service de documentation
   n'écrit dans `agents.json` que la clé `description` ».

## Critères d'acceptation
- [ ] `test_agents_md_is_given_and_editable_when_claude_md_is` (dans `backend/tests/test_documentation_claude_md.py`) : avec `doc_claude_md`, `AGENTS.md` est fourni à doc-technique et son édition est appliquée ; sans, il n'est ni fourni ni écrit
- [ ] `test_description_rewrites_only_its_key` (dans un fichier de test nommé d'après le module qui écrit la description) : le service remplace `description` dans un `agents.json` qui en a une, l'ajoute s'il n'en a pas, et tout autre octet du fichier est identique
- [ ] `test_description_over_220_chars_or_multiline_is_refused` : le fichier n'est pas modifié et le refus est dans le résultat du lot
- [ ] `test_description_without_proof_is_refused` : une description sans extrait de preuve n'est pas écrite
- [ ] `agents/prompts/doc-technique.md` décrit le champ `description` et quand le proposer
- [ ] `memory/contraintes.md` porte la règle sous `## Proposées`, et `memory/decisions.md` une ADR au prochain numéro libre qui la justifie

## Ce que ça ne fait pas
- Ne donne à aucun agent le droit d'écrire `agents.json` : c'est le service qui écrit la seule clé `description`
- Ne change pas le moment de la documentation (par run approuvé, ticket-198)
