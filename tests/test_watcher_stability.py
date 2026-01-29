"""
Tests unitaires pour la logique de file stability (taille inchangée N secondes).
"""
import tempfile
import time
from pathlib import Path

import pytest

from basic_scanner.watcher import StableFileHandler


class TestStableFileHandler:
    """Tests du handler de stabilité fichier."""

    def test_ignore_non_pdf(self):
        """Les fichiers non-PDF sont ignorés."""
        called = []

        def on_stable(path: Path) -> None:
            called.append(path)

        handler = StableFileHandler(on_stable, stability_seconds=0.1, check_interval=0.05)
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = Path(f.name)
        try:
            handler._schedule_check(path)
            # Pas de callback car pas PDF
            handler._check_pending()
            assert len(called) == 0
        finally:
            path.unlink(missing_ok=True)

    def test_stability_after_unchanged_size(self):
        """Après N secondes sans changement de taille, le callback est appelé."""
        called = []

        def on_stable(path: Path) -> None:
            called.append(path)

        handler = StableFileHandler(on_stable, stability_seconds=0.2, check_interval=0.05)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf content")
            f.flush()
            path = Path(f.name)
        try:
            handler._schedule_check(path)
            assert handler.get_pending_count() == 1
            time.sleep(0.25)
            handler._check_pending()
            assert len(called) == 1
            assert called[0].resolve() == path.resolve()
            assert handler.get_pending_count() == 0
        finally:
            path.unlink(missing_ok=True)

    def test_no_callback_if_size_changes(self):
        """Si la taille change avant N secondes, pas de callback (fichier encore en écriture)."""
        called = []

        def on_stable(path: Path) -> None:
            called.append(path)

        handler = StableFileHandler(on_stable, stability_seconds=0.5, check_interval=0.1)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"content")
            f.flush()
            path = Path(f.name)
        try:
            handler._schedule_check(path)
            time.sleep(0.2)
            # Simuler une modification (taille change)
            path.write_text("more content now")
            time.sleep(0.4)
            handler._check_pending()
            # Le délai a été réinitialisé par le changement de taille
            assert len(called) == 0
        finally:
            path.unlink(missing_ok=True)
