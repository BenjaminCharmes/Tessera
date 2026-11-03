"""What a delivery rebase did on its own, as steps of the delivery journal."""


def noter_ce_que_le_rebase_a_fait(
    git: object,
    etapes: list[str],
    durees_ms: list[float],
    resolus: list[str],
) -> None:
    """Appends one step per renumbered migration and per rule-settled conflict.

    Reads `migrations_renumerotees` and `regles_appliquees` off the workspace
    (absent on a double: nothing to note). A rule-settled file joins `resolus`
    like a resolver's: ADR-033 keeps its PR from merging alone, nobody having
    reread it either.
    """
    for ancien, nouveau in getattr(git, "migrations_renumerotees", ()):
        etapes.append(
            f"migration renumérotée : {ancien.rpartition('/')[2]}"
            f" → {nouveau.rpartition('/')[2]}"
        )
        durees_ms.append(0.0)
    for fichier, regle in getattr(git, "regles_appliquees", ()):
        etapes.append(f"conflit résolu par règle : {fichier} ({regle})")
        durees_ms.append(0.0)
        if fichier not in resolus:
            resolus.append(fichier)
