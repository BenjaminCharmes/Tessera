# Leçons du projet

Pièges observés sur ce projet, une ligne chacun. Le service écrit sous `## Proposées` ; un humain déplace une leçon sous `## En vigueur` pour qu'elle atteigne le codeur et le reviewer.

## Proposées
- Quand une validation ignore un pattern de ligne (comme `+++`), ajouter un préfixe pour le contourner crée une dépendance tacite qui se brisera si ce détail change. (source : ticket-862, 2026-11-05)
- Quand tu modifies un modèle Pydantic d'endpoint FastAPI, régénère et commite le schéma OpenAPI. (source : ticket-864, 2026-11-05)

## En vigueur
