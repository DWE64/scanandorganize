"""
CLI BASIC Scanner : run (surveillance) et test-file (traitement d'un fichier).
"""
import fnmatch
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from basic_scanner.classify import compute_confidence, ensure_type_doc
from basic_scanner.config import (
    get_dossier_a_classer,
    get_dossier_failed,
    get_inbox_path,
    get_racine_destination,
    load_config,
)
from basic_scanner.extract import extract_all
from basic_scanner.logging_conf import get_logger, setup_logging
from basic_scanner.mover import move_to_a_classer, move_to_destination, move_to_failed
from basic_scanner.ocr import extract_text_from_pdf
from basic_scanner.rules import (
    build_destination_filename,
    build_destination_path,
    get_filename_template_for_dest,
    get_rule_for_type,
)
from basic_scanner.suppliers import resolve_fournisseur
from basic_scanner.watcher import run_watcher

logger = get_logger("main")

# --- Pipeline de traitement ---


def process_one_pdf(
    pdf_path: Path,
    config: dict,
    dry_run: bool = False,
) -> Optional[dict]:
    """
    Traite un PDF : OCR, extraction, classification, déplacement.
    Retourne un dict avec le résultat (dest_path, extracted, error) ou None en cas d'échec.
    En cas d'exception non récupérable, déplace vers FAILED.
    """
    inbox = get_inbox_path(config)
    racine = get_racine_destination(config)
    a_classer = get_dossier_a_classer(config)
    failed = get_dossier_failed(config)
    modele_chemin = config.get("modele_chemin", "Factures_fournisseurs/{fournisseur}/{YYYY}/{MM}")
    mapping = config.get("mapping_fournisseurs") or {}
    ocr_lang = config.get("ocr_lang", "fra+eng")

    if not pdf_path.is_file():
        logger.error("Fichier introuvable: %s", pdf_path)
        return None

    try:
        # 1. Extraire le texte (OCR si nécessaire)
        texte = extract_text_from_pdf(pdf_path, lang=ocr_lang)
        if not texte or len(texte.strip()) < 10:
            logger.warning("Texte extrait vide ou très court pour %s", pdf_path.name)

        # 2. Extraction des métadonnées
        extracted = extract_all(texte)
        resolve_fournisseur(extracted, mapping)
        extracted.confidence = compute_confidence(extracted)
        ensure_type_doc(extracted)

        # 3. Décision : arborescence existante (règle) ou dossier par défaut (A_CLASSER)
        # A_CLASSER = uniquement quand aucune règle ne fournit d'arborescence pour ce document.
        # FAILED = tout document qui échoue au tri ou au déplacement (vers arborescence ou A_CLASSER).
        rule = get_rule_for_type(extracted.type_document, config)
        has_arborescence = rule and (rule[0] or "").strip()

        if has_arborescence:
            modele_chemin_doc = rule[0]
            modele_nom_doc = (rule[1] or config.get("modele_nom_fichier", "")).strip() or None
            dest_dir = build_destination_path(racine, modele_chemin_doc, extracted, config)
            modele_nom_dest = modele_nom_doc or get_filename_template_for_dest(dest_dir, config)
            dest_filename = build_destination_filename(modele_nom_dest, extracted, config)
            result = move_to_destination(pdf_path, dest_dir, dest_filename, extracted, dry_run=dry_run)
            if not dry_run and result.moved:
                print(f"[Déplacement] {pdf_path.resolve()} -> {result.dest_dir / result.dest_filename}", flush=True)
        else:
            # Aucune arborescence pour ce document → dossier par défaut A_CLASSER
            result = move_to_a_classer(pdf_path, a_classer, extracted, dry_run=dry_run, write_metadata=True)
            if not dry_run and result.moved:
                dest_full = result.dest_dir / result.dest_filename
                print(f"[Déplacement] {pdf_path.resolve()} -> {dest_full.resolve()} (A_CLASSER)", flush=True)

        # Échec du déplacement (vers arborescence ou A_CLASSER) → FAILED
        if result.error and not dry_run:
            failed_path = move_to_failed(pdf_path, failed, result.error, dry_run=False)
            if failed_path:
                print(f"[Déplacement FAILED] {pdf_path.resolve()} -> {failed_path.resolve()} (raison: {result.error})", flush=True)
            return {"error": result.error, "extracted": extracted.to_dict()}

        out = {
            "dest_path": str(result.dest_path()) if result.moved else None,
            "dest_dir": str(result.dest_dir),
            "dest_filename": result.dest_filename,
            "extracted": extracted.to_dict(),
            "moved": result.moved,
        }
        if dry_run:
            out["dry_run"] = True
        return out
    except Exception as e:
        logger.exception("Erreur traitement %s: %s", pdf_path, e)
        if not dry_run:
            failed_path = move_to_failed(pdf_path, failed, str(e), dry_run=False)
            if failed_path:
                print(f"[Déplacement FAILED] {pdf_path.resolve()} -> {failed_path.resolve()} (raison: {e})", flush=True)
        return {"error": str(e), "extracted": {}}


def on_stable_file_factory(config: dict):
    """Fabrique le callback appelé quand un fichier est stable dans l'INBOX."""
    def on_stable_file(path: Path) -> None:
        process_one_pdf(path, config, dry_run=False)
    return on_stable_file


def _should_exclude(path: Path, exclude_patterns: list[str]) -> bool:
    """True si le fichier doit être exclu (tmp, ~, .part, etc.)."""
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(path.name, pattern):
            return True
    return False


def _scan_existing_pdfs(
    inbox: Path,
    callback: Callable[[Path], None],
    exclude_patterns: list[str],
    stability_seconds: float,
) -> None:
    """
    Traite les PDF déjà présents dans l'INBOX au démarrage (après un délai de stabilité).
    Ainsi les fichiers déposés avant le lancement de la surveillance sont aussi triés.
    """
    time.sleep(stability_seconds)
    if not inbox.is_dir():
        return
    for path in inbox.iterdir():
        if not path.is_file() or path.suffix.lower() != ".pdf":
            continue
        if _should_exclude(path, exclude_patterns):
            continue
        try:
            logger.info("Traitement fichier existant au démarrage: %s", path.name)
            callback(path)
        except Exception as e:
            logger.exception("Erreur traitement fichier existant %s: %s", path, e)


# --- CLI ---


def cmd_run(config_path: str, log_file: Optional[str] = None) -> None:
    """Lance la surveillance du dossier INBOX."""
    config = load_config(config_path)
    log_dir = Path(config_path).resolve().parent
    setup_logging(
        log_file=log_file or config.get("log_file"),
        log_dir=Path(config["log_dir"]) if config.get("log_dir") else log_dir,
    )
    inbox = get_inbox_path(config)
    if not inbox.is_dir():
        inbox.mkdir(parents=True, exist_ok=True)
        logger.info("Dossier INBOX créé: %s", inbox)
    get_dossier_a_classer(config).mkdir(parents=True, exist_ok=True)
    get_dossier_failed(config).mkdir(parents=True, exist_ok=True)
    stability_seconds = float(config.get("stability_seconds", 5))
    check_interval = float(config.get("stability_check_interval", 1))
    exclude = config.get("exclude_patterns") or ["*.tmp", "~*", "*.part"]
    callback = on_stable_file_factory(config)
    observer = run_watcher(
        inbox,
        callback,
        stability_seconds=stability_seconds,
        check_interval=check_interval,
        exclude_patterns=exclude,
    )
    # Traiter les PDF déjà présents dans l'INBOX au démarrage (optionnel)
    if config.get("scan_existing_on_start", True):
        def run_scan_existing():
            _scan_existing_pdfs(inbox, callback, exclude, stability_seconds)
        threading.Thread(target=run_scan_existing, daemon=True).start()
        logger.info("Scan des fichiers existants dans l'INBOX activé (après %s s)", stability_seconds)
    try:
        observer.join()
    except KeyboardInterrupt:
        logger.info("Arrêt demandé (Ctrl+C)")
        observer.stop()
        observer.join(timeout=5)


def cmd_test_file(
    pdf_path: str,
    config_path: str,
    dry_run: bool = True,
) -> None:
    """Traite un seul fichier et affiche le résultat (sans déplacer si --dry-run)."""
    config = load_config(config_path)
    setup_logging()
    path = Path(pdf_path)
    if not path.is_file():
        print(f"Fichier introuvable: {path}", file=sys.stderr)
        sys.exit(1)
    result = process_one_pdf(path, config, dry_run=dry_run)
    if result is None:
        sys.exit(2)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    """Point d'entrée CLI."""
    import argparse
    parser = argparse.ArgumentParser(prog="basic_scanner", description="Classement automatique de documents scannés (100% local)")
    parser.add_argument("--config", "-c", default="config.yaml", help="Fichier de configuration YAML")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Lancer la surveillance du dossier INBOX")
    run_p.add_argument("--config", "-c", default="config.yaml", help="Fichier de configuration")
    run_p.add_argument("--log-file", default=None, help="Fichier de log (optionnel)")

    test_p = sub.add_parser("test-file", help="Traiter un seul fichier PDF (affichage résultat)")
    test_p.add_argument("path", help="Chemin du PDF")
    test_p.add_argument("--config", "-c", default="config.yaml", help="Fichier de configuration")
    test_p.add_argument("--no-dry-run", action="store_true", help="Effectuer le déplacement (par défaut: dry-run)")

    args = parser.parse_args()
    if args.command == "run":
        cmd_run(args.config, getattr(args, "log_file", None))
    elif args.command == "test-file":
        cmd_test_file(args.path, args.config, dry_run=not getattr(args, "no_dry_run", True))


if __name__ == "__main__":
    main()
