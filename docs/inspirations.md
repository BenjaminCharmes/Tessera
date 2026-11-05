# Inspirations

Les outils externes dont les consignes de Tessera reprennent des idées, la
version relevée à la reprise et les fichiers qui en dérivent. La règle est dans
l'ADR-077 : aucun outil n'est suivi en direct, une nouvelle version donne un
ticket de relecture, jamais une mise à jour automatique.

Une ligne `Fichiers dérivés` ne cite que des chemins du dépôt, entre accents
graves ; `test_inspirations.py` vérifie qu'ils existent.

## Humanizer

| Champ | Valeur |
| --- | --- |
| Dépôt | `blader/humanizer` |
| Version reprise | `v3.1.0`, commit `0ef9fe5bc357` du 28/10/2026 |
| Date de reprise | 30/10/2026 (ticket-715) |
| Mode | `idées réécrites` |
| Licence | à confirmer sur le dépôt ; sans effet tant que rien n'est recopié |
| Fichiers dérivés | `agents/prompts/doc-fonctionnelle.md` |

Ce qui est repris : les tournures qui trahissent un texte de modèle (insistance,
ternaires, conclusion qui résume, gras d'insistance, emoji), dans « Comment
écrire ».

## Impeccable

| Champ | Valeur |
| --- | --- |
| Dépôt | `pbakaus/impeccable` |
| Version reprise | `cli-v4.8.0` du 26/10/2026, commit `df3a4abe7d08` |
| Date de reprise | 30/10/2026 (ticket-715) |
| Mode | `idées réécrites` |
| Licence | à confirmer sur le dépôt ; sans effet tant que rien n'est recopié |
| Fichiers dérivés | `agents/plugin/skills/design-ui/SKILL.md` |

Ce qui est repris : les défauts qui signent une interface produite par un modèle
(police et accent par défaut, verre dépoli, grille de trois cartes, rayon unique,
chiffres inventés), dans les §4 et §7 du skill.
