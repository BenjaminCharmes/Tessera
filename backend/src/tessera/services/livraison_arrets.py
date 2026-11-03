"""Les messages d'arrêt de la livraison, sortis de `livraison.py` (ticket-568).

Ce sont des phrases pures : elles lisent l'état du service et ne décident de
rien. Les garder à côté du code qui enchaîne les étapes faisait grossir un
fichier déjà au plafond du cliquet de longueur.
"""

#: Le run que le reviewer a refusé ne se livre pas (ADR-030).
ARRET_NON_APPROUVE = (
    "Run non approuvé : son commit porte du travail que le "
    "reviewer a refusé, il ne se livre pas."
)


def arret_niveau_commit(branch: str) -> str:
    """The stop line of a project that declares the `commit` autonomy level."""
    return (
        f"Le travail est commité sur {branch}. Ce projet ne laisse "
        "pas l'IDE aller plus loin ; pour changer cela, déclare "
        '`"autonomy": "pr"` dans son agents.json.'
    )


def arret_conflit(
    base_branch: str,
    conflits: tuple[str, ...],
    resolus: list[str],
    resolveur_cable: bool,
    raison: object,
) -> str:
    """The stop line of an unresolved conflict, saying what the resolver did.

    Sans cela, un résolveur jamais appelé et un résolveur tenté en échec
    donnent la même ligne (ticket-453). `raison` est ce que le rebase a retenu
    de l'échec du résolveur, quand il l'a retenu.
    """
    message = f"Conflit avec {base_branch} sur : " + ", ".join(conflits)
    if not resolveur_cable:
        message += " — résolveur non tenté : aucun résolveur câblé sur cette livraison"
    elif resolus:
        message += (
            f" — résolveur tenté sur {', '.join(resolus)}, sans succès"
            + (f" : {raison}" if isinstance(raison, str) and raison else "")
        )
    else:
        message += " — résolveur non tenté : le rebase ne l'a pas appelé"
    return message + ". La branche est restée intacte, à toi de trancher."


def arret_ci_illisible(code_http: object, pr_number: int) -> str:
    """Le message d'arrêt quand le jeton ne peut pas lire la CI (ticket-449)."""
    precision = f" (HTTP {code_http})" if isinstance(code_http, int) else ""
    return (
        "Le jeton GitHub de Tessera ne peut pas lire la CI de ce dépôt"
        f"{precision} : il lui faut les permissions Actions et Commit "
        f"statuses en lecture. La PR #{pr_number} reste "
        "ouverte, rien n'est mergé."
    )


def arret_pr_en_conflit(pr_number: int, base_branch: str) -> str:
    """The stop line of a PR the CI found in conflict with its base (ticket-452)."""
    return (
        f"PR #{pr_number} en conflit avec {base_branch} : "
        "à rebaser. La PR reste ouverte."
    )
