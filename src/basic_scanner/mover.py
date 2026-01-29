"""
Déplacement / renommage des fichiers avec gestion des collisions.
Ne jamais supprimer : en cas d'erreur → FAILED.
"""
import json
import shutil
from pathlib import Path
from typing import Optional

from basic_scanner.logging_conf import get_logger
from basic_scanner.models import ExtractedData, ProcessingResult

logger = get_logger("mover")


def _ensure_dir(path: Path) -> None:
    """Crée le répertoire (et parents) si nécessaire. Supporte UNC."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error("Impossible de créer le dossier %s: %s", path, e)
        raise


def _unique_path(dest_dir: Path, base_name: str) -> Path:
    """Retourne un chemin unique : si le fichier existe, ajoute un suffixe _1, _2, ..."""
    dest = dest_dir / base_name
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    i = 1
    while True:
        candidate = dest_dir / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def move_to_destination(
    source_path: Path,
    dest_dir: Path,
    dest_filename: str,
    extracted: ExtractedData,
    dry_run: bool = False,
) -> ProcessingResult:
    """
    Déplace et renomme le fichier vers dest_dir/dest_filename.
    Gère les collisions (suffixe _1, _2...). En cas d'erreur, ne supprime pas le fichier.
    """
    result = ProcessingResult(
        source_path=source_path,
        dest_dir=dest_dir,
        dest_filename=dest_filename,
        extracted=extracted,
        moved=False,
    )
    if dry_run:
        result.dest_filename = dest_filename
        return result

    if not source_path.is_file():
        result.error = f"Fichier source introuvable: {source_path}"
        return result

    try:
        _ensure_dir(dest_dir)
        final_path = _unique_path(dest_dir, dest_filename)
        shutil.move(str(source_path), str(final_path))
        result.dest_filename = final_path.name
        result.moved = True
        final_path_resolved = final_path.resolve()
        logger.info("Déplacement: %s -> %s", source_path.resolve(), final_path_resolved)
        return result
    except Exception as e:
        result.error = str(e)
        logger.error("Erreur déplacement %s: %s", source_path, e)
        return result


def move_to_a_classer(
    source_path: Path,
    dossier_a_classer: Path,
    extracted: ExtractedData,
    dry_run: bool = False,
    write_metadata: bool = True,
) -> ProcessingResult:
    """
    Déplace le fichier vers A_CLASSER avec nom standard :
    {timestamp}_A_CLASSER_{original}.pdf
    et écrit un .json à côté avec les métadonnées extraites.
    """
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = source_path.name
    safe_name = original_name[:80] if len(original_name) > 80 else original_name
    dest_filename = f"{timestamp}_A_CLASSER_{safe_name}"

    result = ProcessingResult(
        source_path=source_path,
        dest_dir=dossier_a_classer,
        dest_filename=dest_filename,
        extracted=extracted,
        moved=False,
    )
    if dry_run:
        return result

    if not source_path.is_file():
        result.error = f"Fichier source introuvable: {source_path}"
        return result

    try:
        _ensure_dir(dossier_a_classer)
        final_path = _unique_path(dossier_a_classer, dest_filename)
        shutil.move(str(source_path), str(final_path))
        result.dest_filename = final_path.name
        result.moved = True

        if write_metadata:
            meta_path = final_path.with_suffix(final_path.suffix + ".json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(extracted.to_dict(), f, ensure_ascii=False, indent=2)
        final_path_resolved = final_path.resolve()
        logger.info("Déplacement (A_CLASSER): %s -> %s", source_path.resolve(), final_path_resolved)
        return result
    except Exception as e:
        result.error = str(e)
        logger.error("Erreur A_CLASSER %s: %s", source_path, e)
        return result


def move_to_failed(
    source_path: Path,
    dossier_failed: Path,
    error_message: str,
    dry_run: bool = False,
) -> Optional[Path]:
    """
    Déplace le fichier vers FAILED (exceptions non récupérables).
    Nom : {original}_FAILED.pdf ou avec suffixe si collision.
    """
    if dry_run:
        return dossier_failed / f"{source_path.name}_FAILED"

    if not source_path.is_file():
        logger.error("Fichier introuvable pour FAILED: %s", source_path)
        return None

    try:
        _ensure_dir(dossier_failed)
        base = source_path.stem + "_FAILED" + source_path.suffix
        final_path = _unique_path(dossier_failed, base)
        shutil.move(str(source_path), str(final_path))
        final_path_resolved = final_path.resolve()
        logger.error("Déplacement (FAILED): %s -> %s (raison: %s)", source_path.resolve(), final_path_resolved, error_message)
        return final_path
    except Exception as e:
        logger.exception("Impossible de déplacer vers FAILED: %s", source_path)
        return None
