"""
Point d'entrée unique pour l'exécutable BASIC Scanner (PyInstaller).
- Sans argument ou avec des arguments non "run" : lance l'interface graphique (scan_gui).
- Avec l'argument "run" : lance la surveillance (basic_scanner run).
Permet un seul .exe pour l'interface et le watcher.
"""
import os
import sys
from pathlib import Path


def main():
    if getattr(sys, "frozen", False):
        # Mode exécutable (PyInstaller) : répertoire de base = dossier de l'exe
        base = Path(sys.executable).resolve().parent
        os.chdir(base)
        if len(sys.argv) >= 2 and sys.argv[1].strip().lower() == "run":
            # Mode surveillance : déléguer à basic_scanner
            from basic_scanner.main import main as scanner_main
            scanner_main()
            return
        # Mode interface graphique : créer config dans un dossier réservé (invisible pour l'utilisateur)
        if sys.platform == "win32":
            config_dir = Path(os.environ.get("LOCALAPPDATA", "") or str(Path.home() / "AppData" / "Local")) / "BASIC Scanner"
        elif sys.platform == "darwin":
            config_dir = Path.home() / "Library" / "Application Support" / "BASIC Scanner"
        else:
            config_dir = Path(os.environ.get("XDG_CONFIG_HOME", "") or str(Path.home() / ".config")) / "BASIC Scanner"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_yaml = config_dir / "config.yaml"
        if not config_yaml.is_file():
            _meipass = Path(getattr(sys, "_MEIPASS", ""))
            if _meipass:
                example = _meipass / "config.example.yaml"
                if example.is_file():
                    import shutil
                    shutil.copy2(example, config_yaml)
        if str(base) not in sys.path:
            sys.path.insert(0, str(base))
        import scan_gui
        scan_gui.main()
        return

    # Mode développement : répertoire de base = racine du projet
    base = Path(__file__).resolve().parent
    os.chdir(base)
    if str(base / "src") not in sys.path:
        sys.path.insert(0, str(base / "src"))
    import scan_gui
    scan_gui.main()


if __name__ == "__main__":
    main()
