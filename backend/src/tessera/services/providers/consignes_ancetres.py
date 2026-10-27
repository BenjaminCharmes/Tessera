from pathlib import Path

# Les fichiers de consignes que Claude Code charge dans chaque dossier ancêtre.
_FICHIERS_CONSIGNES = ("CLAUDE.md", "CLAUDE.local.md")


def claude_md_ancetres_a_exclure(
    cwd: Path, racine: Path, ancestor: bool
) -> list[str]:
    """Lists the ancestor CLAUDE files a hosted project must not inherit.

    Claude Code walks up from ``cwd`` and loads every ``CLAUDE.md`` it meets, so
    the IDE's own rules would leak into each project nested under ``racine``
    (ticket-414). Returns the ``CLAUDE.md`` and ``CLAUDE.local.md`` of every
    directory from ``racine`` down to ``cwd``'s parent, as absolute ``/`` paths.
    Empty when the project is ``ancestor`` (it needs those rules) or when
    ``cwd`` is not strictly under ``racine``.
    """
    if ancestor:
        return []
    projet = cwd.resolve()
    depart = racine.resolve()
    if projet == depart or not projet.is_relative_to(depart):
        return []
    dossiers = [p for p in projet.parents if p.is_relative_to(depart)]
    return [
        (dossier / nom).as_posix()
        for dossier in reversed(dossiers)
        for nom in _FICHIERS_CONSIGNES
    ]
