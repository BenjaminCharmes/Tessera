---
id: ticket-715
title: "Shipped prompts name the defaults of generic AI output"
type: docs
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-30
---

# ticket-715 — Les consignes livrées nomment les défauts d'une sortie IA générique

## Objectif
Donner au codeur des projets front et à `doc-fonctionnelle` la liste des
défauts qui signent une interface ou un texte produits par un modèle, sans
ajouter d'outil ni de dépendance.

## Contexte
Benjamin a repéré plusieurs outils populaires qui traitent ce problème :
Impeccable, Taste Skill, Hallmark et UI/UX Pro Max pour le design, et
Humanizer pour le texte. Vérifiés le 30/10 :
- Impeccable télécharge un binaire, interroge son catalogue en ligne même
  télémétrie coupée et installe des hooks.
- Humanizer fait environ 4 500 mots, soit à peu près 6 000 tokens, qui
  partiraient dans chaque appel du rôle.
- `tessera:design-ui` §4 porte déjà une liste anti-défauts, chargée par le
  codeur, l'architecte et le reviewer des projets front.

On reprend donc les idées, réécrites, dans les deux consignes existantes.
Aucun texte n'est recopié.

Écartés au même examen :
- Scrapling pour Affût : son ADR-004 exclut le contournement des protections,
  et la base comptait 0 offre bloquée sur 33 relevés.
- Last 30 Days : il demande des clés, lit les cookies du navigateur et ne
  vise que macOS.

Les titres de PR et les messages de commit ne passent par aucun modèle
(`pr_title`) : Humanizer ne les concerne pas.

## Fait (à la main : `agents/plugin/` et les prompts se livrent par PR)
- `agents/plugin/skills/design-ui/SKILL.md` §4 : police et accent par défaut,
  verre dépoli et halo, grille de trois cartes, rayon unique, accroche et
  chiffres inventés, animation d'apparition. §7 : relecture en audit, chaque
  élément justifié par une donnée ou une action.
- `agents/prompts/doc-fonctionnelle.md`, « Comment écrire » : tournures qui
  trahissent un modèle (insistance, ternaires, « permet de », conclusion
  résumée, gras d'insistance, emoji).

## Critères d'acceptation
- [x] Le diff ne touche que les deux fichiers ci-dessus et ce ticket
- [x] `design-ui` reste sous 1 000 mots, `doc-fonctionnelle.md` sous 1 000 mots
- [x] `test_skills_par_role.py` et `test_consignes_coherentes.py` passent

## Ce que ça ne fait pas
- Aucune passe sur l'existant : la règle vaut pour les tickets suivants.
- Aucun nouveau skill ni aucune nouvelle déclaration dans `agents.json`.
- Pas de détecteur automatique : le reviewer et le validateur jugent.
