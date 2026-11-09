# Leçons du projet

Pièges observés sur ce projet, une ligne chacun. Le service écrit sous `## Proposées` ; un humain déplace une leçon sous `## En vigueur` pour qu'elle atteigne le codeur et le reviewer.

## Proposées
- Quand on abaisse le plafond de longueur d'un fichier lors d'une refactorisation, mesurer le bilan net en lignes avant de soumettre — l'extraction seule peut ne pas suffire. (source : ticket-875, 2026-11-06)
- Quand on ajoute du logging via `get_logger()`, vérifier d'abord que ce log sera visible aux tests avant de les écrire. (source : ticket-880, 2026-11-06)
- Quand on protège un chemin sans développer les variables d'environnement et le ~, la protection peut être contournée. (source : ticket-879, 2026-11-06)
- Quand on centralise une fonction et l'importe partout, vérifier que chaque fichier reste sous 300 lignes. (source : ticket-888, 2026-11-06)
- Quand une mise à jour SDK est corrigée après rejet, soumettre avec le lockfile complet et le rapport d'API, pas l'un sans l'autre. (source : ticket-893, 2026-11-09)
- Quand une fonction n'est appelée que sous condition, la tester en franchissant cette condition, jamais en l'appelant isolément. (source : ticket-892, 2026-11-09)
- Quand les gardes de permission se multiplient dans agent_sdk.py, créer une fonction qui agrège les hooks pour respecter le plafond. (source : ticket-899, 2026-11-09)

## En vigueur
- Quand tu ajoutes ou modifies une route ou un modèle de réponse FastAPI, régénère et commite `docs/openapi.json`, et range la route dans `frontend/src/test/contrat/perimetre.ts` (couverte ou hors périmètre). (source : ticket-860, ticket-864, 2026-11-06)
- Quand un ticket ferme une voie d'attaque ou une porte (route, commande, chemin), liste dans le diff ou le ticket toutes les routes, commandes et chemins de la même classe et ferme-les ou dis pourquoi ils restent ouverts : une faille corrigée sur une seule route laisse sa voisine ouverte. (source : ticket-808 vs PATCH /pipeline, audit externe, 2026-11-06)
