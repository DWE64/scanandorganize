"""
Chargement et validation de la configuration YAML.
"""
from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: str | Path) -> dict[str, Any]:
    """
    Charge et retourne la configuration depuis un fichier YAML.
    :param config_path: Chemin vers le fichier config (relatif ou absolu, UNC supporté).
    :return: Dictionnaire de configuration.
    :raises FileNotFoundError: Si le fichier n'existe pas.
    :raises yaml.YAMLError: Si le YAML est invalide.
    """
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Fichier de configuration introuvable: {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}

    return _normalize_config(data, path.parent)


def _normalize_config(data: dict[str, Any], config_dir: Path) -> dict[str, Any]:
    """
    Normalise les chemins relatifs par rapport au répertoire du fichier config.
    Supporte les chemins UNC (\\\\NAS\\Partage\\...).
    """
    out = dict(data)

    # INBOX : peut être relatif au config ou absolu/UNC
    inbox = out.get("inbox")
    if inbox:
        p = Path(inbox)
        if not p.is_absolute():
            p = (config_dir / p).resolve()
        out["inbox"] = str(p)

    # Racine destination
    racine = out.get("racine_destination")
    if racine:
        p = Path(racine)
        if not p.is_absolute():
            p = (config_dir / p).resolve()
        out["racine_destination"] = str(p)

    # Dossiers A_CLASSER et FAILED (optionnels, relatifs à racine ou absolus)
    for key in ("dossier_a_classer", "dossier_failed"):
        val = out.get(key)
        if val:
            p = Path(val)
            if not p.is_absolute() and out.get("racine_destination"):
                p = Path(out["racine_destination"]) / p
            out[key] = str(p)

    return out


def get_inbox_path(config: dict[str, Any]) -> Path:
    """Retourne le chemin INBOX en tant que Path."""
    return Path(config["inbox"])


def get_racine_destination(config: dict[str, Any]) -> Path:
    """Retourne la racine de destination."""
    return Path(config["racine_destination"])


def get_dossier_a_classer(config: dict[str, Any]) -> Path:
    """Retourne le dossier A_CLASSER (défaut: racine/A_CLASSER)."""
    return Path(config.get("dossier_a_classer") or config["racine_destination"] + "/A_CLASSER")


def get_dossier_failed(config: dict[str, Any]) -> Path:
    """Retourne le dossier FAILED (défaut: racine/FAILED)."""
    return Path(config.get("dossier_failed") or config["racine_destination"] + "/FAILED")


def save_config(config: dict[str, Any], config_path: str | Path) -> None:
    """
    Enregistre la configuration dans un fichier YAML.
    :param config: Dictionnaire de configuration (chemins absolus ou relatifs).
    :param config_path: Chemin du fichier de sortie.
    """
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
