---
agent: codeur
created: 2026-10-10
depends_on: []
estimated_days: 1
id: ticket-395
pr_number: null
priority: medium
status: done
title: A doc agent whose edits are refused gets one corrective round with the exact
  headings, and section anchors tolerate case and spacing
type: fix
---

# ticket-395 — Un agent de doc refusé a droit à un tour de correction

## Objectif

Que la documentation de fin de file aboutisse quand un agent de doc a visé un
texte ou une section qui n'existe pas, au lieu d'être perdue en entier.

## Contexte

`DocumentationService.mettre_a_jour`
(`backend/src/tessera/services/documentation.py`) envoie à `doc-technique` et
à `doc-fonctionnelle` les tickets et le contenu actuel de la doc
(ticket-228). `appliquer_editions` applique toutes les éditions d'un agent ou
aucune : un seul `ancien` ou `apres_section` introuvable fait refuser tout le
lot de cet agent.

Signalé par la session qui pilote affut le 2026-10-10 : sur affut 008, 012 et
014 (2026-10-08), éditions refusées à chaque ticket — « docs/guide-utilisateur.md :
texte introuvable — « ## Prochaines étapes » ». La fin de file a demandé un
ticket de doc entier (affut 020).

## Solution proposée

1. **Tour de correction** : quand `appliquer_editions` lève `EditionRefusee`
   pour un agent, le rappeler **une seule fois** avec son brief, sa réponse
   précédente, le motif du refus et, pour le fichier visé, la liste exacte de
   ses titres Markdown (`_titres_markdown`). Si le second lot est refusé à
   son tour, le comportement actuel s'applique (refus journalisé).
2. **Ancrage tolérant** : `_inserer` reconnaît la section quand le titre
   correspond après normalisation (casse, espaces multiples, espaces en fin
   de ligne), à niveau de titre égal. Un titre ambigu (deux correspondances)
   reste refusé.
3. `ResultatDocumentation` dit si un tour de correction a eu lieu ; la ligne
   de journal de la documentation le mentionne.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_documentation.py` simule un agent dont la première réponse vise une section absente et la seconde une section existante, et vérifie que la seconde est appliquée
- [ ] Un test de `backend/tests/test_documentation.py` vérifie que le second appel reçoit le motif du refus et la liste des titres du fichier visé
- [ ] Un test de `backend/tests/test_documentation.py` vérifie qu'un agent refusé deux fois n'est pas rappelé une troisième fois et que son refus est conservé
- [ ] Un test de `backend/tests/test_documentation.py` vérifie qu'un `apres_section` « ## prochaines  étapes » trouve la section « ## Prochaines étapes »
- [ ] Un test de `backend/tests/test_documentation.py` vérifie qu'un `apres_section` qui correspond à deux titres après normalisation est refusé

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Un appel LLM de plus par agent refusé, au plus un : borné, et moins cher
qu'un ticket de doc entier.

## Ce que ça ne fait pas

- Ne passe pas à une application partielle des éditions : tout ou rien reste
  la règle par agent.
- Ne change pas les prompts des agents de doc.