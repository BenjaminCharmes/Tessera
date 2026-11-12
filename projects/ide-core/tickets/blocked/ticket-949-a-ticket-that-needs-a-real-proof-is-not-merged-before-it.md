---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 1
id: ticket-949
pr_number: null
priority: high
status: blocked
title: A ticket that needs a real proof stops at its PR, and the validator does not
  judge that proof
type: fix
---

# ticket-949 — Un ticket qui demande une preuve réelle s'arrête à sa PR, et le validateur ne juge pas cette preuve

## Objectif

Qu'un ticket qui touche les processus, les comptes, les droits ou l'OS ne
soit mergé qu'après une preuve faite sur la machine par un humain ou par la
session ide-core, et que ce critère ne bloque plus le validateur.

## Contexte

Le 12/11, la chaîne du compte agent (tickets 894, 895, 915, 934) était
approuvée et mergée, tests verts. Le premier lancement réel a échoué trois
fois, sur des points que les doubles de test ne voyaient pas : la limite de
1 024 caractères, les chemins sous le profil, l'absence de job. À l'inverse,
le ticket-946 portait un critère « preuve sur la machine », et le validateur
l'a refusé trois tours de suite : aucun agent ne peut fournir cette preuve.

Décision de Benjamin du 12/11 : un ticket système porte une preuve réelle,
vérifiée avant le merge, pas par le validateur.

## Solution proposée

1. `Ticket` (`models/ticket.py`) gagne `preuve_reelle: bool = False`, déclaré
   dans le frontmatter comme `plan` ou `light`.
2. Le corps d'un tel ticket porte une section `## Preuve réelle` (ce qu'il
   faut lancer et constater). Le validateur ne reçoit pas cette section :
   seuls les `## Critères d'acceptation` lui sont donnés, comme aujourd'hui.
3. Livraison : un run approuvé d'un ticket `preuve_reelle` pousse sa branche
   et ouvre sa PR, mais ne la confie pas au merge automatique, même en
   autonomie `merge`. Le corps de la PR recopie la section `## Preuve réelle`,
   et le journal du pipeline écrit « PR ouverte, merge après preuve réelle ».

## Critères d'acceptation

- [ ] Un test : un frontmatter avec `preuve_reelle: true` se charge, et la
      valeur par défaut est `False`.
- [ ] Un test : le brief du validateur pour un ticket qui a une section
      `## Preuve réelle` ne contient pas le texte de cette section.
- [ ] Un test : en autonomie `merge`, un ticket `preuve_reelle` approuvé
      ouvre sa PR et n'est pas confié au merge automatique ; la `Livraison`
      porte un arrêt voulu qui le dit.
- [ ] Un test : sans `preuve_reelle`, la livraison ne change pas.

## Ce que ça ne fait pas

- N'automatise pas la preuve : elle reste faite et constatée par un humain
  ou par la session ide-core.
- Ne change pas les autres niveaux d'autonomie.
- Ne touche pas le skill `new-ticket` : le pipeline refuse aux agents
  `.claude/` ; la session ide-core y décrit le champ à la main après le merge
  (premier run bloqué le 12/11 sur ce critère).