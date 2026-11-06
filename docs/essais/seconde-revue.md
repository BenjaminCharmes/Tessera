# Essai d'une seconde revue par un autre modèle

Corpus : 23 entrées, gel `ffda8f86cd7038873db5cb9310ae8ee8e355343c35c69b631013f1161b03a092`.

## Par bras

| bras | appels | ok | verdicts levés | coût moyen ($) | coût max ($) | durée moyenne (ms) | durée max (ms) |
|---|---|---|---|---|---|---|---|
| B | 23 | 23 | 8 | 0.2803 | 0.4172 | 30164 | 43516 |
| C | 23 | 23 | 4 | 0.0000 | 0.0000 | 107154 | 221672 |

## Comptes

- rejeu valide : non
- défauts en plus : 0 (dont 0 sensibles)
- faux positifs en plus : 0 (dont 0 sensibles)
- durée ajoutée par revue : 107154 ms
- coût moyen : C 0.0000 $, B 0.2803 $

## Conclusion

<!-- seconde-revue-conclusion:debut -->
**Recommandation : non concluant.** rejeu non valide : B approuve trop peu ou C exclut trop.

C'est une recommandation : l'ADR qui décide appartient à un humain.
<!-- seconde-revue-conclusion:fin -->

## Conditions du rejeu

- **Bras B** : le reviewer actuel d'ide-core, `agent_sdk:claude-opus-5-5`, rejoué le 06/11 :
  23 appels en 12 min, 6,45 $ au total (plafond du ticket : 10 $).
- **Bras C** : le candidat `ollama:qwen3-coder:30b`, local, rejoué le 06/11 :
  fenêtre de 96 000 caractères (32 000 tokens × 3), 23 appels en 41 min, 0 $.
- Les 46 lignes portent le même gel du corpus.
- Relecture à l'aveugle par Benjamin : 17 remarques mêlées dans un ordre tiré au
  sort, sans nom de modèle, sans bras, sans la classe de l'entrée.

## Pourquoi « non concluant »

Le seuil qui échoue est **l'approbation de B** : 15 entrées approuvées sur 23
(65 %), pour 80 % exigés. Le seuil d'exclusion de C tient (aucune entrée
exclue).

B a refusé 5 entrées classées « saines » : s02, s09, s10, s11 et s12. La relecture
humaine a **confirmé ses 12 remarques**, sur ces 5 entrées comme sur les 3 entrées à
défaut. Ces 5 commits n'étaient donc pas sains : c'est le classement du corpus qui
a cédé, pas le reviewer.

## Ce que montre la relecture, au-delà de la règle

| | remarques | confirmées | infondées |
|---|---|---|---|
| B (Opus 5.5) | 12 | 12 | 0 |
| C (qwen3-coder:30b) | 5 | 0 | 5 |

C n'a trouvé aucun des défauts que B avait laissés passer (d03, d07, d08 : remarques
infondées), et il a levé une fausse alerte sur s11. Il ajoute environ 107 s par
revue. Même avec un corpus valide, il n'aurait rien apporté sur ces 23 entrées.

## Limites

- 23 entrées : un petit échantillon.
- Le rejeu est sans outils : le reviewer lit le ticket et le diff, il n'explore pas
  le dépôt comme en production.
- Un seul humain a relu.
- Le style des remarques peut trahir le modèle malgré l'anonymat.

## Ce qui est proposé ensuite

- Ne pas brancher `qwen3-coder:30b` en seconde revue : ni l'ADR qui amenderait
  ADR-009 et ADR-061, ni le ticket de branchement.
- Revoir les 5 commits « sains » que B a refusés (tickets 547, 305, 185, 130, 432) :
  vérifier si ces défauts existent encore sur `develop`, un ticket par défaut
  encore présent.
- Si l'on veut un jour un essai concluant, reclasser le corpus avant de le rejouer.
