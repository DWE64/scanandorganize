"""
Configuration du logging : fichier + console, niveaux INFO/ERROR.
"""
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_file: Optional[str | Path] = None,
    level: int = logging.INFO,
    log_dir: Optional[Path] = None,
) -> None:
    """
    Configure le logging : console (INFO) + fichier optionnel.
    :param log_file: Nom du fichier de log (ex: basic_scanner.log).
    :param level: Niveau global (INFO par défaut).
    :param log_dir: Dossier des logs (si log_file relatif).
    """
    root = logging.getLogger("basic_scanner")
    root.setLevel(level)

    # Éviter double handlers si appel multiple
    if root.handlers:
        return

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # Fichier (optionnel)
    if log_file:
        path = Path(log_file)
        if not path.is_absolute() and log_dir:
            path = log_dir / path
        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(fmt)
        root.addHandler(fh)


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger enfant de basic_scanner."""
    return logging.getLogger(f"basic_scanner.{name}")
