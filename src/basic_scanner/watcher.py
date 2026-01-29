"""
Surveillance du dossier INBOX (watchdog) + file stability check.
Détecte les nouveaux PDF, attend que la taille soit stable pendant N secondes avant traitement.
"""
import fnmatch
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from basic_scanner.logging_conf import get_logger

logger = get_logger("watcher")


def _matches_exclude(path: Path, exclude_patterns: list[str]) -> bool:
    """True si le fichier doit être exclu (tmp, ~, .part, etc.)."""
    name = path.name
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


class StableFileHandler(FileSystemEventHandler):
    """
    Gère les événements de création/modification et déclenche le callback
    uniquement quand le fichier est "stable" (taille inchangée pendant N secondes).
    """

    def __init__(
        self,
        on_stable_file: Callable[[Path], None],
        stability_seconds: float = 5.0,
        check_interval: float = 1.0,
        min_file_size: int = 0,
        exclude_patterns: Optional[list[str]] = None,
    ):
        super().__init__()
        self.on_stable_file = on_stable_file
        self.stability_seconds = stability_seconds
        self.check_interval = check_interval
        self.min_file_size = min_file_size
        self.exclude_patterns = exclude_patterns or ["*.tmp", "~*", "*.part"]
        # Fichiers en attente : path -> (last_size, last_check_time)
        self._pending: dict[Path, tuple[int, float]] = {}

    def _is_pdf(self, path: Path) -> bool:
        return path.suffix.lower() == ".pdf"

    def _should_ignore(self, path: Path) -> bool:
        if not self._is_pdf(path):
            return True
        if _matches_exclude(path, self.exclude_patterns):
            return True
        try:
            if path.stat().st_size < self.min_file_size:
                return True
        except OSError:
            return True
        return False

    def _schedule_check(self, path: Path) -> None:
        """Enregistre le fichier pour une vérification de stabilité."""
        path = path.resolve()
        if path in self._pending:
            return
        try:
            size = path.stat().st_size
        except OSError:
            return
        self._pending[path] = (size, time.monotonic())
        logger.debug("Fichier en attente (stabilité): %s", path.name)

    def _check_pending(self) -> None:
        """Parcourt les fichiers en attente et déclenche le callback si stables."""
        now = time.monotonic()
        to_remove = []
        to_process = []

        for path, (last_size, last_check) in list(self._pending.items()):
            try:
                if not path.exists():
                    to_remove.append(path)
                    continue
                size = path.stat().st_size
            except OSError:
                to_remove.append(path)
                continue

            if size != last_size:
                # Taille changée : mettre à jour et repartir le délai
                self._pending[path] = (size, now)
                continue

            elapsed = now - last_check
            if elapsed >= self.stability_seconds:
                to_remove.append(path)
                to_process.append(path)

        for p in to_remove:
            self._pending.pop(p, None)

        for path in to_process:
            if path.exists() and not self._should_ignore(path):
                logger.info("Fichier stable, traitement: %s", path.name)
                try:
                    self.on_stable_file(path)
                except Exception as e:
                    logger.exception("Erreur dans on_stable_file pour %s: %s", path, e)

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._should_ignore(path):
            return
        self._schedule_check(path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._should_ignore(path):
            return
        self._schedule_check(path)

    def get_pending_count(self) -> int:
        return len(self._pending)


def run_watcher(
    inbox_path: Path,
    on_stable_file: Callable[[Path], None],
    stability_seconds: float = 5.0,
    check_interval: float = 1.0,
    min_file_size: int = 0,
    exclude_patterns: Optional[list[str]] = None,
) -> Observer:
    """
    Démarre l'observer watchdog et un thread de vérification de stabilité.
    Retourne l'Observer (à appeler observer.start() puis observer.join() ou stop()).
    """
    handler = StableFileHandler(
        on_stable_file=on_stable_file,
        stability_seconds=stability_seconds,
        check_interval=check_interval,
        min_file_size=min_file_size,
        exclude_patterns=exclude_patterns,
    )
    observer = Observer()
    observer.schedule(handler, str(inbox_path), recursive=False)

    # Thread ou timer pour _check_pending : on utilise un thread dédié simple
    import threading

    stop_flag = threading.Event()

    def stability_loop() -> None:
        while not stop_flag.wait(handler.check_interval):
            handler._check_pending()

    stability_thread = threading.Thread(target=stability_loop, daemon=True)
    stability_thread.start()

    # Stocker pour pouvoir arrêter plus tard (optionnel)
    observer._stability_stop = stop_flag  # type: ignore
    observer._stability_thread = stability_thread  # type: ignore

    observer.start()
    logger.info("Surveillance INBOX: %s (stabilité %s s)", inbox_path, stability_seconds)
    return observer
