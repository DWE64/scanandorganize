"""
BASIC Scanner - Interface graphique d'installation (Windows).
Fenêtre avec progression et notification de fin. Utilise uniquement la bibliothèque standard (tkinter).
Lancer avec : python install_gui.py  (depuis la racine du projet)
"""
import os
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path

# Tkinter (stdlib)
try:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import messagebox
    from tkinter import font as tkfont
except ImportError:
    print("Erreur : tkinter est requis. Installez Python avec les composants optionnels (tcl/tk).")
    sys.exit(1)

# Racine du projet = dossier contenant ce script
PROJECT_ROOT = Path(__file__).resolve().parent
VENV_PATH = PROJECT_ROOT / ".venv"

# Sous Windows : ne pas afficher de fenêtre console pour les processus enfants (pip, venv, etc.)
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if sys.platform == "win32" else 0
SUBPROCESS_KW = {"creationflags": CREATE_NO_WINDOW} if sys.platform == "win32" else {}
CONFIG_YAML = PROJECT_ROOT / "config.yaml"
CONFIG_EXAMPLE = PROJECT_ROOT / "config.example.yaml"
SCAN_GUI_SCRIPT = PROJECT_ROOT / "scan_gui.py"
SHORTCUT_NAME = "BASIC Scanner"

# Étapes pour la progression (texte, pourcentage max après cette étape)
STEPS = [
    ("Vérification de Python...", 10),
    ("Création de l'environnement virtuel...", 25),
    ("Installation des dépendances (cela peut prendre 1 à 2 minutes)...", 60),
    ("Création du fichier de configuration...", 75),
    ("Vérification des prérequis (Tesseract, Ghostscript)...", 90),
    ("Finalisation...", 95),
]


def get_pythonw_path():
    """Retourne le chemin de pythonw (sans fenêtre console) pour lancer l'interface."""
    if sys.platform == "win32" and VENV_PATH.exists():
        pw = VENV_PATH / "Scripts" / "pythonw.exe"
        if pw.exists():
            return str(pw)
    # Fallback: pythonw dans le PATH ou même répertoire que python
    if sys.platform == "win32":
        return "pythonw"
    return sys.executable


def create_shortcut():
    """
    Crée un raccourci pour lancer l'interface (Bureau ou menu Démarrer selon l'OS).
    Retourne (True, message) ou (False, message).
    """
    pythonw = get_pythonw_path()
    target = str(SCAN_GUI_SCRIPT)
    if not Path(target).exists():
        return False, "Fichier scan_gui.py introuvable."
    work_dir = str(PROJECT_ROOT)

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            CSIDL_DESKTOP = 0
            SHGFP_TYPE_CURRENT = 0
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(0, CSIDL_DESKTOP, 0, SHGFP_TYPE_CURRENT, buf)
            desktop = buf.value
            lnk_path = str(Path(desktop) / (SHORTCUT_NAME + ".lnk"))
            # Script .ps1 temporaire (here-string PowerShell : @' doit être suivi d'un saut de ligne)
            def ps_escape(s):
                return (s or "").replace("'", "''")
            ps1 = PROJECT_ROOT / "_create_shortcut.ps1"
            ps1.write_text(
                """$lnk = @'
""" + ps_escape(lnk_path) + """
'@
$exe = @'
""" + ps_escape(pythonw) + """
'@
$target = @'
""" + ps_escape(target) + """
'@
$wd = @'
""" + ps_escape(work_dir) + """
'@
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($lnk)
$s.TargetPath = $exe
$s.Arguments = $target
$s.WorkingDirectory = $wd
$s.Description = "BASIC Scanner"
$s.Save()
""",
                encoding="utf-8",
            )
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=work_dir,
                    **SUBPROCESS_KW,
                )
                if r.returncode == 0 and Path(lnk_path).exists():
                    return True, f"Raccourci créé : Bureau\\{SHORTCUT_NAME}.lnk"
                return False, r.stderr or r.stdout or "Échec création raccourci"
            finally:
                ps1.unlink(missing_ok=True)
        except Exception as e:
            return False, str(e)
    elif sys.platform == "darwin":
        # Mac : créer un .command qui lance l'interface
        desktop = Path.home() / "Desktop"
        cmd_file = desktop / (SHORTCUT_NAME.replace(" ", "") + ".command")
        try:
            cmd_file.write_text(
                f"#!/bin/bash\ncd {repr(work_dir)}\nexec {repr(pythonw)} {repr(target)}\n",
                encoding="utf-8",
            )
            cmd_file.chmod(0o755)
            return True, f"Raccourci créé : Bureau\\{cmd_file.name}"
        except Exception as e:
            return False, str(e)
    else:
        # Linux : .desktop
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            desktop = Path.home() / ".local" / "share" / "applications"
        desktop.mkdir(parents=True, exist_ok=True)
        desk_file = desktop / (SHORTCUT_NAME.lower().replace(" ", "_") + ".desktop")
        try:
            desk_file.write_text(
                f"""[Desktop Entry]
Type=Application
Name={SHORTCUT_NAME}
Comment=Interface de classement de documents scannés
Exec={pythonw} {target}
Path={work_dir}
Terminal=false
""",
                encoding="utf-8",
            )
            desk_file.chmod(0o755)
            return True, f"Raccourci créé : {desk_file}"
        except Exception as e:
            return False, str(e)


def launch_ui_no_console():
    """Lance l'interface utilisateur sans afficher de terminal."""
    pythonw = get_pythonw_path()
    target = str(SCAN_GUI_SCRIPT)
    work_dir = str(PROJECT_ROOT)
    kwargs = {"cwd": work_dir, "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        kwargs["creationflags"] = CREATE_NO_WINDOW
    try:
        subprocess.Popen([pythonw, target], **kwargs)
        return True
    except Exception:
        return False


def find_python():
    """Retourne le chemin ou la commande Python 3.11+."""
    for cmd in ("python", "python3", "py"):
        try:
            r = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(PROJECT_ROOT),
                **SUBPROCESS_KW,
            )
            out = (r.stdout or r.stderr or "").strip()
            if "3.11" in out or "3.12" in out or "3.13" in out:
                return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
    # Fallback : Python actuel
    if sys.version_info >= (3, 11):
        return sys.executable
    return None


def run_install(steps_queue: queue.Queue, run_tests: bool) -> None:
    """Exécute l'installation dans un thread. Envoie (step_index, label, progress_pct) ou (None, error_msg, -1)."""
    try:
        python_cmd = find_python()
        if not python_cmd:
            steps_queue.put((None, "Python 3.11 ou supérieur est requis.", -1))
            return

        # Étape 1 : Python
        steps_queue.put((0, STEPS[0][0], 10))

        # Étape 2 : venv
        steps_queue.put((1, STEPS[1][0], 25))
        if not VENV_PATH.exists():
            subprocess.run(
                [python_cmd, "-m", "venv", str(VENV_PATH)],
                check=True,
                capture_output=True,
                timeout=120,
                cwd=str(PROJECT_ROOT),
                **SUBPROCESS_KW,
            )
        python_exe = str(VENV_PATH / "Scripts" / "python.exe")
        pip_cmd = [python_exe, "-m", "pip"]

        # Étape 3 : pip install
        steps_queue.put((2, STEPS[2][0], 60))
        subprocess.run(
            pip_cmd + ["install", "-e", ".[dev]", "-q"],
            check=True,
            capture_output=True,
            timeout=300,
            cwd=str(PROJECT_ROOT),
            **SUBPROCESS_KW,
        )

        # Étape 4 : config
        steps_queue.put((3, STEPS[3][0], 75))
        if not CONFIG_YAML.exists() and CONFIG_EXAMPLE.exists():
            shutil.copy2(CONFIG_EXAMPLE, CONFIG_YAML)

        # Étape 5 : prérequis (informatif, pas bloquant)
        steps_queue.put((4, STEPS[4][0], 90))

        # Étape 6 : tests optionnels
        steps_queue.put((5, STEPS[5][0], 95))
        if run_tests:
            subprocess.run(
                [python_exe, "-m", "pytest", "tests/", "-v", "--tb=line", "-q"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                timeout=120,
                **SUBPROCESS_KW,
            )

        steps_queue.put((len(STEPS), "Installation terminée.", 100))
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode("utf-8", errors="replace") if e.stderr else str(e)
        steps_queue.put((None, f"Erreur lors de l'installation : {err[:200]}", -1))
    except Exception as e:
        steps_queue.put((None, f"Erreur : {e}", -1))


class InstallerWindow:
    """Fenêtre principale de l'installateur."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BASIC Scanner - Installation")
        self.root.resizable(False, False)
        self.root.minsize(480, 220)
        self.root.geometry("500x260")

        # Centrer la fenêtre
        self.root.update_idletasks()
        w, h = 500, 260
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.steps_queue = queue.Queue()
        self.install_done = False
        self.error_msg = None

        self._build_ui()
        self._start_install()

    def _build_ui(self):
        """Construit l'interface."""
        main = ttk.Frame(self.root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        title_font = tkfont.Font(weight="bold", size=12)
        ttk.Label(main, text="BASIC Scanner", font=title_font).pack(anchor=tk.W)
        ttk.Label(main, text="Installation en cours...", foreground="gray").pack(anchor=tk.W)

        ttk.Separator(main, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(10, 15))

        self.status_var = tk.StringVar(value="Préparation...")
        self.status_label = ttk.Label(main, textvariable=self.status_var, wraplength=440)
        self.status_label.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))

        self.progress = ttk.Progressbar(main, length=440, mode="determinate", maximum=100)
        self.progress.pack(fill=tk.X, pady=(0, 15))
        self.progress["value"] = 0

        ttk.Separator(main, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 15))

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X)
        self.close_btn = ttk.Button(btn_frame, text="Fermer", command=self._on_close, state=tk.DISABLED)
        self.close_btn.pack(side=tk.RIGHT)

    def _start_install(self):
        """Lance l'installation dans un thread."""
        self.worker = threading.Thread(
            target=run_install,
            args=(self.steps_queue, False),
            daemon=True,
        )
        self.worker.start()
        self._poll_queue()

    def _poll_queue(self):
        """Lit la file des mises à jour et met à jour l'interface (appelé depuis le thread principal)."""
        try:
            while True:
                msg = self.steps_queue.get_nowait()
                step_index, label, progress = msg
                if step_index is None:
                    self.error_msg = label
                    self.progress["value"] = 0
                    self.status_var.set(f"Échec : {label[:80]}")
                    self.install_done = True
                    self.close_btn["state"] = tk.NORMAL
                    messagebox.showerror("Installation échouée", label, parent=self.root)
                    return
                self.status_var.set(label)
                self.progress["value"] = progress
                if progress >= 100:
                    self.install_done = True
                    self.progress["value"] = 100
                    self._show_finish_in_same_window()
                    return
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    def _show_finish_in_same_window(self):
        """Affiche les options (raccourci, lancer, fermer) dans la même fenêtre."""
        self.status_var.set("Installation terminée avec succès.")
        self.progress.pack_forget()
        self.root.geometry("520x360")
        main_frame = self.root.winfo_children()[0]
        self.finish_frame = ttk.Frame(main_frame, padding=0)
        self.finish_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(self.finish_frame, text="Que souhaitez-vous faire ?", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))
        btn_row1 = ttk.Frame(self.finish_frame)
        btn_row1.pack(fill=tk.X, pady=4)
        ttk.Button(btn_row1, text="Créer un raccourci sur le Bureau", command=self._do_create_shortcut).pack(side=tk.LEFT, padx=(0, 8))
        btn_row2 = ttk.Frame(self.finish_frame)
        btn_row2.pack(fill=tk.X, pady=4)
        ttk.Button(btn_row2, text="Lancer l'interface maintenant", command=self._do_launch_ui).pack(side=tk.LEFT)
        self.close_btn["state"] = tk.NORMAL

    def _do_create_shortcut(self):
        ok, msg = create_shortcut()
        if ok:
            messagebox.showinfo("Raccourci", msg, parent=self.root)
        else:
            messagebox.showwarning("Raccourci", f"Impossible de créer le raccourci : {msg}", parent=self.root)

    def _do_launch_ui(self):
        if launch_ui_no_console():
            messagebox.showinfo("Lancement", "L'interface a été lancée.", parent=self.root)
        else:
            messagebox.showwarning("Lancement", "Impossible de lancer l'interface.", parent=self.root)

    def _on_close(self):
        """Fermeture de la fenêtre."""
        if self.install_done or self.error_msg:
            self.root.destroy()
        else:
            if messagebox.askyesno(
                "Quitter ?",
                "L'installation est encore en cours. Voulez-vous vraiment quitter ?",
                parent=self.root,
            ):
                self.root.destroy()

    def run(self):
        """Boucle principale."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()


def main():
    os.chdir(PROJECT_ROOT)
    app = InstallerWindow()
    app.run()


if __name__ == "__main__":
    main()
