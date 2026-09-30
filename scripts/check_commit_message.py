"""Validate commit messages against Conventional Commits in a Git hook."""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

from rich.console import Console

LOGGER = logging.getLogger(__name__)
CONVENTIONAL_COMMIT = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(\([^)]+\))?!?: .+"
)


def is_conventional_commit(message: str) -> bool:
    """Return whether a message uses the Conventional Commits subject form.

    Parameters
    ----------
    message : str
        Complete Git commit message; only its first line is validated.

    Returns
    -------
    bool
        True when the subject has a recognized type, optional scope, colon,
        space, and non-empty description.

    Raises
    ------
    None

    Notes
    -----
    The accepted type vocabulary covers common code, documentation, test,
    build, CI, and maintenance changes.
    """
    subject = message.splitlines()[0] if message.splitlines() else ""
    return CONVENTIONAL_COMMIT.fullmatch(subject) is not None


def main(arguments: list[str] | None = None) -> int:
    """Validate the commit message file supplied by Git's commit-msg hook.

    Parameters
    ----------
    arguments : list of str or None, default=None
        Hook arguments; defaults to command-line arguments.

    Returns
    -------
    int
        Zero for a valid message, one for invalid hook input.

    Raises
    ------
    OSError
        If Git's message file cannot be read.

    Notes
    -----
    Rich writes concise feedback to the hook's terminal; the validator itself
    can also be imported and tested without invoking Git.
    """
    argv = sys.argv[1:] if arguments is None else arguments
    console = Console(stderr=True)
    if not argv:
        console.print("[red]Commit message file argument is required.[/red]")
        return 1
    message = Path(argv[0]).read_text(encoding="utf-8")
    if not is_conventional_commit(message):
        console.print(
            "[red]Use a Conventional Commit subject, e.g. "
            "'docs: explain analysis methodology'.[/red]"
        )
        return 1
    LOGGER.info("Commit message format is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
