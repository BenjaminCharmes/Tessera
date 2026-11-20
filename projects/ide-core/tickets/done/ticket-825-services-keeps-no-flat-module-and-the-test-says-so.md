---
id: ticket-825
title: "Services keeps no flat module and the test says so"
type: refactor
status: done
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-824]
estimated_days: 1
created: 2026-11-05
---

# ticket-825 — `services/` ne garde aucun module à plat, et le test le dit

## Objectif

Le classement de départ devient la règle définitive : plus de table de transition, plus de script de
déplacement, un module à plat ne passe plus.

## Contexte

ADR-076. Les tickets 803 à 818 ont vidé `A_DEPLACER`. Reste la règle sans son échafaudage.

## Ce que le ticket fait

- Déplace `ORDRE` de `scripts/domaines_services.py` dans `backend/tests/test_domaines_services.py`,
  supprime `A_DEPLACER` et le module de données.
- Remplace le test de couverture : tout fichier directement sous `services/`, hors `__init__.py`,
  fait échouer ; chaque dossier de `services/` figure dans `ORDRE`, chaque entrée d'`ORDRE` est un
  dossier.
- Supprime `scripts/deplacer_domaine.py` et son test, et `memory/services-domaines.md` (la liste
  est devenue l'arborescence).
- Vérifie que `contraintes.md` (règle d'ADR-076) dit la même chose que le test, sans la recopier.

## Critères d'acceptation

- [x] Un fichier posé à plat sous `services/` fait échouer `test_domaines_services.py`
- [x] `scripts/domaines_services.py`, `scripts/deplacer_domaine.py`, `test_deplacer_domaine.py` et
      `memory/services-domaines.md` n'existent plus
- [x] `ORDRE` du test porte les dix-huit domaines, dans l'ordre d'ADR-076
- [x] La suite passe, `ECARTS_DOMAINES` n'a grandi d'aucune ligne

## Ce que ça ne fait pas

Aucun module ne bouge. Les écarts restants de `ECARTS_DOMAINES` se corrigent un à un, hors de ce
ticket, et la liste ne fait que diminuer.

## Notes de réalisation

Écart : `services/anomalies/` (détecteur d'anomalies, tickets 832 à 840, né après le classement) n'était dans aucun domaine, et le nouveau test refuse un dossier hors d'ORDRE. Il passe sous `services/supervision/anomalies/` : il observe les runs, comme la salle Tessera qui compte ses anomalies, et importe `pipeline`, ce que seul `supervision` permet. C'est le seul module déplacé par ce ticket ; ORDRE garde ses dix-huit domaines. `scripts/deplacer_domaine_texte.py`, utilitaire du script de déplacement, est supprimé avec lui. Reste hors de ce ticket, faute de droit d'écriture : `contraintes.md` (règle d'ADR-076) et ADR-076 dans `decisions.md` renvoient encore à `memory/services-domaines.md`, supprimé ; la règle dit par ailleurs la même chose que le test (domaine, sens des imports, quatre paquets de premier niveau). Le renvoi est à remplacer par `backend/tests/test_domaines_services.py` (ORDRE).
