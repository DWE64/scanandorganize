"""
BASIC Scanner - Interface graphique de visualisation.
Affiche : dossier scanné (INBOX), racine cible, arborescence et fichiers.
Lancer : python scan_gui.py  (depuis la racine du projet, avec venv activé)
"""
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import messagebox
    from tkinter import filedialog
    from tkinter import font as tkfont
except ImportError:
    print("Erreur : tkinter est requis.")
    sys.exit(1)

# Racine du projet (dossier de l'exe en mode PyInstaller, sinon dossier du script)
def _project_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _config_default():
    """Chemin du fichier de config : dossier réservé en mode exe (invisible), sinon à la racine du projet."""
    if getattr(sys, "frozen", False):
        import os
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", "") or str(Path.home() / "AppData" / "Local")) / "BASIC Scanner"
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "BASIC Scanner"
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", "") or str(Path.home() / ".config")) / "BASIC Scanner"
        return base / "config.yaml"
    return _project_root() / "config.yaml"


PROJECT_ROOT = _project_root()
CONFIG_DEFAULT = _config_default()

# Limite d'éléments pour éviter blocage (arborescence)
MAX_TREE_NODES = 5000
MAX_DEPTH = 15

# Clés intégrées (placeholders) et leur description pour la fenêtre d'aide
CLES_INTEGREES = [
    ("fournisseur", "Nom du fournisseur détecté sur le document (normalisé pour dossiers)"),
    ("client", "Identifiant client (même valeur que fournisseur, pour règles facture_client)"),
    ("impots", "Sous-dossier impôts (fournisseur si type impots, sinon « impots »)"),
    ("YYYY", "Année extraite du document (4 chiffres)"),
    ("MM", "Mois (01-12)"),
    ("DD", "Jour du mois (01-31)"),
    ("numero", "Numéro de facture ou de document"),
    ("montant", "Montant TTC formaté"),
    ("type_doc", "Type de document (FACT, AVR, DEVIS, COURRIER, PLAN, IMPOTS, INCONNU)"),
]


def load_config_safe(path):
    """Charge la config sans lever d'exception (retourne None si erreur)."""
    try:
        if not getattr(sys, "frozen", False) and str(PROJECT_ROOT / "src") not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from basic_scanner.config import load_config
        return load_config(path)
    except Exception:
        return None


def save_config_safe(config, path):
    """Sauvegarde la config (retourne True/False)."""
    try:
        if not getattr(sys, "frozen", False) and str(PROJECT_ROOT / "src") not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from basic_scanner.config import save_config
        save_config(config, path)
        return True
    except Exception:
        return False


def build_tree_entries(root_path, max_nodes=MAX_TREE_NODES, max_depth=MAX_DEPTH):
    """
    Construit la liste (parent_id, name, full_path, is_dir, node_id) pour le TreeView.
    node_id = numéro unique (string) pour éviter problèmes avec chemins dans iid.
    Retourne: list of (parent_id, name, full_path, is_dir, node_id), ordre BFS.
    """
    root_path = Path(root_path)
    if not root_path.is_dir():
        return []
    root_str = str(root_path.resolve())
    entries = []
    node_ids = {root_str: "0"}
    try:
        stack = [(root_str, 0)]  # (path, depth)
        node_count = 1
        while stack and node_count < max_nodes:
            current_path, depth = stack.pop(0)
            if depth > max_depth:
                continue
            try:
                current = Path(current_path)
            except Exception:
                continue
            # Id du répertoire courant (parent des enfants qu'on va ajouter)
            parent_id = node_ids.get(current_path, "0")
            try:
                children = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
                for child in children:
                    if node_count >= max_nodes:
                        break
                    cid = str(node_count)
                    node_ids[str(child)] = cid
                    node_count += 1
                    entries.append((parent_id, child.name, str(child), child.is_dir(), cid))
                    if child.is_dir():
                        stack.append((str(child), depth + 1))
            except (PermissionError, OSError):
                pass
    except Exception:
        pass
    return entries, node_ids


def list_dir_simple(path, max_files=2000):
    """Liste (nom, chemin, is_dir) pour un dossier. Limité à max_files."""
    path = Path(path)
    if not path.is_dir():
        return []
    result = []
    try:
        for p in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if len(result) >= max_files:
                result.append((f"... et plus ({max_files} max)", "", False))
                break
            result.append((p.name, str(p), p.is_dir()))
    except (PermissionError, OSError):
        result.append(("(accès refusé)", "", False))
    return result


class ScannerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BASIC Scanner - Visualisation")
        self.root.minsize(800, 550)
        self.root.geometry("1000x600")
        self.config_path = CONFIG_DEFAULT
        self.config_data = {}
        self.tree_queue = queue.Queue()
        self.inbox_queue = queue.Queue()
        self._build_ui()
        self._load_config_ui()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # --- Configuration (tout dans l'interface, pas d'édition YAML) ---
        cfg = ttk.LabelFrame(main, text="Configuration — tout se configure ici", padding=8)
        cfg.pack(fill=tk.X, pady=(0, 8))

        nb = ttk.Notebook(cfg)
        nb.pack(fill=tk.X, pady=(0, 8))

        # Onglet Dossiers et arborescence
        tab_dossiers = ttk.Frame(nb, padding=4)
        nb.add(tab_dossiers, text="Dossiers et arborescence")
        ttk.Label(tab_dossiers, text="Dossier scanné (INBOX) :").pack(anchor=tk.W)
        row_inbox = ttk.Frame(tab_dossiers)
        row_inbox.pack(fill=tk.X)
        self.var_inbox = tk.StringVar()
        ttk.Entry(row_inbox, textvariable=self.var_inbox, width=70).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Button(row_inbox, text="Parcourir…", command=self._browse_inbox).pack(side=tk.LEFT)
        ttk.Label(tab_dossiers, text="Racine cible (où seront rangés les fichiers) :").pack(anchor=tk.W, pady=(8, 0))
        row_racine = ttk.Frame(tab_dossiers)
        row_racine.pack(fill=tk.X)
        self.var_racine = tk.StringVar()
        ttk.Entry(row_racine, textvariable=self.var_racine, width=70).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Button(row_racine, text="Parcourir…", command=self._browse_racine).pack(side=tk.LEFT)
        ttk.Label(tab_dossiers, text="Règles de classement (type de document → arborescence et format de fichier) :").pack(anchor=tk.W, pady=(8, 0))
        ttk.Label(tab_dossiers, text="Types possibles : facture_fournisseur, avoir, devis, courrier, plan, défaut (pour le reste). Mots dans chemins : fournisseur, YYYY, MM, DD, numero, montant, type_doc", foreground="gray", font=("", 8)).pack(anchor=tk.W)
        f_regles = ttk.Frame(tab_dossiers)
        f_regles.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.regles_tree = ttk.Treeview(f_regles, columns=("type", "chemin", "format"), show="headings", height=5)
        self.regles_tree.heading("type", text="Type de document")
        self.regles_tree.heading("chemin", text="Modèle de chemin (arborescence)")
        self.regles_tree.heading("format", text="Format de nom de fichier")
        self.regles_tree.column("type", width=140)
        self.regles_tree.column("chemin", width=220)
        self.regles_tree.column("format", width=220)
        scroll_r = ttk.Scrollbar(f_regles, orient=tk.VERTICAL, command=self.regles_tree.yview)
        self.regles_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_r.pack(side=tk.RIGHT, fill=tk.Y)
        self.regles_tree.configure(yscrollcommand=scroll_r.set)
        self.regles_tree.bind("<Double-1>", lambda e: self._edit_tree_cell(self.regles_tree, ("type", "chemin", "format"), e))
        btn_r = ttk.Frame(tab_dossiers)
        btn_r.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(btn_r, text="Ajouter une règle", command=self._add_regle_row).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_r, text="Supprimer la règle", command=self._remove_regle_row).pack(side=tk.LEFT)

        # Onglet Formats de fichier
        tab_formats = ttk.Frame(nb, padding=4)
        nb.add(tab_formats, text="Formats de fichier")
        ttk.Label(tab_formats, text="Format de nom de fichier par défaut :").pack(anchor=tk.W)
        self.var_modele_nom = tk.StringVar(value="{YYYY}-{MM}-{DD}_{type_doc}_{fournisseur}_{numero}_{montant}.pdf")
        ttk.Entry(tab_formats, textvariable=self.var_modele_nom, width=70).pack(fill=tk.X, pady=(2, 8))
        ttk.Label(tab_formats, text="Format par dossier (si le fichier va dans ce dossier, utiliser ce format) :").pack(anchor=tk.W)
        f_formats = ttk.Frame(tab_formats)
        f_formats.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.formats_tree = ttk.Treeview(f_formats, columns=("dossier", "format"), show="headings", height=4)
        self.formats_tree.heading("dossier", text="Dossier ou motif")
        self.formats_tree.heading("format", text="Format de nom de fichier")
        self.formats_tree.column("dossier", width=180)
        self.formats_tree.column("format", width=280)
        scroll_f = ttk.Scrollbar(f_formats, orient=tk.VERTICAL, command=self.formats_tree.yview)
        self.formats_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_f.pack(side=tk.RIGHT, fill=tk.Y)
        self.formats_tree.configure(yscrollcommand=scroll_f.set)
        self.formats_tree.bind("<Double-1>", lambda e: self._edit_tree_cell(self.formats_tree, ("dossier", "format"), e))
        btn_f = ttk.Frame(tab_formats)
        btn_f.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(btn_f, text="Ajouter une ligne", command=self._add_format_row).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_f, text="Supprimer la ligne", command=self._remove_format_row).pack(side=tk.LEFT)

        # Onglet Mot-clés et identification de dossiers
        tab_fourn = ttk.Frame(nb, padding=4)
        nb.add(tab_fourn, text="Mot-clés et identification de dossiers")
        ttk.Label(tab_fourn, text="Mapping : mot-clé trouvé sur le document → nom du dossier (pour l'arborescence) :").pack(anchor=tk.W)
        f_fourn = ttk.Frame(tab_fourn)
        f_fourn.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.fourn_tree = ttk.Treeview(f_fourn, columns=("alias", "nom"), show="headings", height=6)
        self.fourn_tree.heading("alias", text="Texte trouvé (alias)")
        self.fourn_tree.heading("nom", text="Nom du dossier")
        self.fourn_tree.column("alias", width=200)
        self.fourn_tree.column("nom", width=150)
        scroll_fourn = ttk.Scrollbar(f_fourn, orient=tk.VERTICAL, command=self.fourn_tree.yview)
        self.fourn_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_fourn.pack(side=tk.RIGHT, fill=tk.Y)
        self.fourn_tree.configure(yscrollcommand=scroll_fourn.set)
        self.fourn_tree.bind("<Double-1>", lambda e: self._edit_tree_cell(self.fourn_tree, ("alias", "nom"), e))
        btn_fourn = ttk.Frame(tab_fourn)
        btn_fourn.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(btn_fourn, text="Ajouter", command=self._add_fourn_row).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_fourn, text="Supprimer", command=self._remove_fourn_row).pack(side=tk.LEFT)

        # Onglet Clés (placeholders) : clés personnalisées modifiables à la volée
        tab_cles = ttk.Frame(nb, padding=4)
        nb.add(tab_cles, text="Clés (placeholders)")
        ttk.Label(tab_cles, text="Clés personnalisées utilisables dans les modèles de chemin et de nom de fichier (ex: {ma_cle}). Double-clic pour modifier.").pack(anchor=tk.W)
        f_cles = ttk.Frame(tab_cles)
        f_cles.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.cles_tree = ttk.Treeview(f_cles, columns=("cle", "description", "valeur"), show="headings", height=5)
        self.cles_tree.heading("cle", text="Clé")
        self.cles_tree.heading("description", text="Description / utilité")
        self.cles_tree.heading("valeur", text="Valeur par défaut")
        self.cles_tree.column("cle", width=120)
        self.cles_tree.column("description", width=280)
        self.cles_tree.column("valeur", width=120)
        scroll_cles = ttk.Scrollbar(f_cles, orient=tk.VERTICAL, command=self.cles_tree.yview)
        self.cles_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_cles.pack(side=tk.RIGHT, fill=tk.Y)
        self.cles_tree.configure(yscrollcommand=scroll_cles.set)
        self.cles_tree.bind("<Double-1>", lambda e: self._edit_tree_cell(self.cles_tree, ("cle", "description", "valeur"), e))
        btn_cles = ttk.Frame(tab_cles)
        btn_cles.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(btn_cles, text="Ajouter une clé", command=self._add_cle_row).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_cles, text="Supprimer la clé", command=self._remove_cle_row).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_cles, text="Aide sur les clés", command=self._show_cles_help).pack(side=tk.LEFT)

        # Boutons Charger / Sauvegarder (fichier config interne, utilisateur n'a pas à connaître le YAML)
        row_actions = ttk.Frame(cfg)
        row_actions.pack(fill=tk.X, pady=(8, 0))
        self.var_config = tk.StringVar(value=str(CONFIG_DEFAULT))
        ttk.Button(row_actions, text="Charger la configuration", command=self._load_config_ui).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(row_actions, text="Sauvegarder la configuration", command=self._save_config).pack(side=tk.LEFT)

        # Surveillance automatique : pastille d'état, lancer / arrêter, journal
        row_watcher = ttk.LabelFrame(cfg, text="Surveillance automatique (tri des PDF)", padding=6)
        row_watcher.pack(fill=tk.X, pady=(10, 0))
        self._watcher_process = None
        self._watcher_stopped_by_user = False
        self._watcher_log = ""
        self._watcher_status_state = "stopped"  # "stopped" | "running" | "error"
        row_watcher_inner = ttk.Frame(row_watcher)
        row_watcher_inner.pack(fill=tk.X)
        # Pastille d'état (couleur : gris / vert / rouge)
        self.canvas_status = tk.Canvas(row_watcher_inner, width=14, height=14, highlightthickness=0)
        self.canvas_status.pack(side=tk.LEFT, padx=(0, 6))
        self._draw_status_dot("stopped")
        self.label_watcher_status = ttk.Label(row_watcher_inner, text="Surveillance arrêtée.", foreground="gray")
        self.label_watcher_status.pack(side=tk.LEFT, padx=(0, 12))
        self.btn_watcher = ttk.Button(row_watcher_inner, text="Lancer la surveillance", command=self._toggle_watcher)
        self.btn_watcher.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_watcher_log = ttk.Button(row_watcher_inner, text="Voir le journal", command=self._show_watcher_log, state=tk.DISABLED)
        self.btn_watcher_log.pack(side=tk.LEFT)
        ttk.Label(row_watcher, text="A_CLASSER = dossier par défaut si aucune arborescence n'existe pour le document. FAILED = documents en échec au tri ou au déplacement.", foreground="gray", font=("", 8)).pack(anchor=tk.W, pady=(6, 0))

        # --- Panneau principal : INBOX + Racine ---
        paned = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        # Gauche : Dossier scanné (INBOX)
        left = ttk.LabelFrame(paned, text="Dossier scanné (INBOX) — contenu", padding=4)
        paned.add(left, weight=1)
        self.inbox_tree = ttk.Treeview(left, height=12, selectmode="browse", show="tree", columns=())
        self.inbox_tree.heading("#0", text="Nom")
        scroll_inbox = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.inbox_tree.yview)
        self.inbox_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_inbox.pack(side=tk.RIGHT, fill=tk.Y)
        self.inbox_tree.configure(yscrollcommand=scroll_inbox.set)
        self.inbox_tree.bind("<<TreeviewSelect>>", self._on_inbox_select)
        self.label_inbox_status = ttk.Label(left, text="Charger la config puis sélectionner INBOX.", foreground="gray")
        self.label_inbox_status.pack(anchor=tk.W)

        # Droite : Racine cible (arborescence + fichiers)
        right = ttk.Frame(paned)
        paned.add(right, weight=2)

        right_top = ttk.LabelFrame(right, text="Racine cible — arborescence", padding=4)
        right_top.pack(fill=tk.BOTH, expand=True)
        self.racine_tree = ttk.Treeview(right_top, height=12, selectmode="browse", show="tree", columns=())
        self.racine_tree.heading("#0", text="Nom")
        scroll_racine = ttk.Scrollbar(right_top, orient=tk.VERTICAL, command=self.racine_tree.yview)
        self.racine_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_racine.pack(side=tk.RIGHT, fill=tk.Y)
        self.racine_tree.configure(yscrollcommand=scroll_racine.set)
        self.racine_tree.bind("<<TreeviewSelect>>", self._on_racine_select)

        right_bottom = ttk.LabelFrame(right, text="Fichiers dans le dossier sélectionné", padding=4)
        right_bottom.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.file_list = tk.Listbox(right_bottom, height=8, selectmode=tk.EXTENDED, font=("Consolas", 9))
        scroll_files = ttk.Scrollbar(right_bottom, orient=tk.VERTICAL, command=self.file_list.yview)
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_files.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_list.configure(yscrollcommand=scroll_files.set)
        self.label_file_status = ttk.Label(right_bottom, text="Sélectionnez un dossier dans l'arborescence.", foreground="gray")
        self.label_file_status.pack(anchor=tk.W)

        self.label_racine_status = ttk.Label(right_top, text="Charger la config pour afficher l'arborescence.", foreground="gray")
        self.label_racine_status.pack(anchor=tk.W)

    def _get_python_exe(self):
        """Retourne le chemin du Python à utiliser (exe en mode frozen, sinon venv prioritaire)."""
        if getattr(sys, "frozen", False):
            return sys.executable
        if os.name == "nt":
            venv_py = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
        else:
            venv_py = PROJECT_ROOT / ".venv" / "bin" / "python"
        if venv_py.exists():
            return str(venv_py)
        return sys.executable

    def _draw_status_dot(self, state):
        """Dessine la pastille de couleur selon l'état (stopped=running=green, error=red)."""
        colors = {"stopped": "#9e9e9e", "running": "#2e7d32", "error": "#c62828"}
        color = colors.get(state, "#9e9e9e")
        self.canvas_status.delete("all")
        self.canvas_status.create_oval(2, 2, 12, 12, fill=color, outline=color)

    def _update_watcher_status(self, state, message):
        """Met à jour la pastille, le message et l'état."""
        self._watcher_status_state = state
        self._draw_status_dot(state)
        self.label_watcher_status.config(text=message)
        if state == "running":
            self.label_watcher_status.config(foreground="green")
        elif state == "error":
            self.label_watcher_status.config(foreground="#c62828")
        else:
            self.label_watcher_status.config(foreground="gray")
        if self._watcher_log.strip():
            self.btn_watcher_log.config(state=tk.NORMAL)
        else:
            self.btn_watcher_log.config(state=tk.DISABLED)

    def _show_watcher_log(self):
        """Ouvre une fenêtre affichant le journal (stdout/stderr) de la dernière exécution."""
        win = tk.Toplevel(self.root)
        win.title("Journal de la surveillance")
        win.geometry("600x400")
        win.transient(self.root)
        f = ttk.Frame(win, padding=8)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text="Sortie de la surveillance (stdout / stderr) :").pack(anchor=tk.W)
        text = tk.Text(f, wrap=tk.WORD, font=("Consolas", 9), state=tk.NORMAL)
        scroll = ttk.Scrollbar(f, orient=tk.VERTICAL, command=text.yview)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(4, 0))
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(4, 0))
        text.configure(yscrollcommand=scroll.set)
        log = getattr(self, "_watcher_log", "") or "(Aucun journal disponible.)"
        text.insert(tk.END, log)
        text.config(state=tk.DISABLED)

    def _toggle_watcher(self):
        """Lance ou arrête la surveillance du dossier INBOX."""
        if self._watcher_process is not None:
            self._watcher_stopped_by_user = True
            try:
                self._watcher_process.terminate()
                self._watcher_process.wait(timeout=5)
            except Exception:
                try:
                    self._watcher_process.kill()
                except Exception:
                    pass
            self._watcher_process = None
            self._update_watcher_status("stopped", "Surveillance arrêtée.")
            self.btn_watcher.config(text="Lancer la surveillance")
            return
        config_path = self.var_config.get().strip() or str(CONFIG_DEFAULT)
        path = Path(config_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if not path.exists():
            messagebox.showwarning(
                "Configuration",
                "Fichier de configuration introuvable. Sauvegardez la configuration ou chargez un fichier valide.",
                parent=self.root,
            )
            return
        self._watcher_stopped_by_user = False
        python_exe = self._get_python_exe()
        if getattr(sys, "frozen", False):
            cmd = [python_exe, "run", "--config", str(path)]
        else:
            cmd = [python_exe, "-m", "basic_scanner", "run", "--config", str(path)]
        kwargs = {
            "cwd": str(PROJECT_ROOT),
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        try:
            self._watcher_process = subprocess.Popen(cmd, **kwargs)
        except Exception as e:
            self._watcher_log = f"Impossible de lancer le processus :\n{e}"
            self._update_watcher_status("error", f"Erreur au lancement : {e}")
            self.btn_watcher_log.config(state=tk.NORMAL)
            messagebox.showerror(
                "Surveillance",
                f"Impossible de lancer la surveillance : {e}",
                parent=self.root,
            )
            return
        self.btn_watcher.config(text="Arrêter la surveillance")
        self._update_watcher_status("running", "Surveillance en cours — les PDF déposés dans l'INBOX seront triés.")

        def watcher_worker(proc):
            try:
                stdout, stderr = proc.communicate(timeout=86400 * 365)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
            except Exception:
                stdout, stderr = b"", b""
            code = proc.returncode
            out_txt = (stdout or b"").decode("utf-8", errors="replace")
            err_txt = (stderr or b"").decode("utf-8", errors="replace")
            log = ""
            if out_txt.strip():
                log += "--- stdout ---\n" + out_txt.strip() + "\n"
            if err_txt.strip():
                log += "--- stderr ---\n" + err_txt.strip() + "\n"
            if not log:
                log = "(Aucune sortie capturée.)"
            self.root.after(0, lambda: self._on_watcher_exited(code, log, self._watcher_stopped_by_user))

        threading.Thread(target=watcher_worker, args=(self._watcher_process,), daemon=True).start()

    def _on_watcher_exited(self, returncode, log, stopped_by_user):
        """Appelé quand le processus de surveillance s'arrête."""
        self._watcher_process = None
        self._watcher_log = log
        try:
            self.btn_watcher.config(text="Lancer la surveillance")
            if stopped_by_user:
                self._update_watcher_status("stopped", "Surveillance arrêtée.")
            elif returncode != 0:
                short = (log.split("\n")[0] if log else "")[:80]
                self._update_watcher_status("error", f"Erreur (code {returncode}). Cliquez sur « Voir le journal » pour les détails.")
                self.btn_watcher_log.config(state=tk.NORMAL)
            else:
                self._update_watcher_status("stopped", "Surveillance arrêtée.")
        except tk.TclError:
            pass

    def _edit_tree_cell(self, tree, column_keys, event):
        """Ouvre une boîte de dialogue pour éditer la cellule cliquée (double-clic)."""
        region = tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = tree.identify_column(event.x)
        if not col or not col.startswith("#"):
            return
        try:
            col_idx = int(col[1:])  # #1 -> 1
        except ValueError:
            return
        if col_idx < 1 or col_idx > len(column_keys):
            return
        item = tree.identify_row(event.y)
        if not item:
            return
        values = list(tree.item(item, "values"))
        if col_idx > len(values):
            return
        current = values[col_idx - 1]
        title = f"Modifier — {column_keys[col_idx - 1]}"
        new_val = self._ask_edit_string(title, current, parent=tree.winfo_toplevel())
        if new_val is not None:
            values[col_idx - 1] = new_val
            tree.item(item, values=values)

    def _ask_edit_string(self, title, initial_value, parent=None):
        """Ouvre une petite fenêtre avec un champ de saisie ; retourne la valeur ou None si annulé."""
        win = tk.Toplevel(parent or self.root)
        win.title(title)
        win.transient(parent or self.root)
        win.grab_set()
        f = ttk.Frame(win, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text="Valeur :").pack(anchor=tk.W)
        var = tk.StringVar(value=initial_value or "")
        entry = ttk.Entry(f, textvariable=var, width=60)
        entry.pack(fill=tk.X, pady=(2, 10))
        entry.focus_set()
        entry.select_range(0, tk.END)
        result = [None]

        def ok():
            result[0] = var.get().strip()
            win.destroy()

        def cancel():
            win.destroy()

        btn_f = ttk.Frame(f)
        btn_f.pack(fill=tk.X)
        ttk.Button(btn_f, text="OK", command=ok).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_f, text="Annuler", command=cancel).pack(side=tk.LEFT)
        win.bind("<Return>", lambda e: ok())
        win.bind("<Escape>", lambda e: cancel())
        win.protocol("WM_DELETE_WINDOW", cancel)
        win.update_idletasks()
        win.geometry(f"+{win.winfo_screenwidth()//2 - 200}+{win.winfo_screenheight()//2 - 80}")
        win.wait_window()
        return result[0]

    def _add_regle_row(self):
        self.regles_tree.insert("", tk.END, values=("facture_fournisseur", "Factures_fournisseurs/{fournisseur}/{YYYY}/{MM}", "{YYYY}-{MM}-{DD}_{type_doc}_{fournisseur}_{numero}.pdf"))

    def _remove_regle_row(self):
        sel = self.regles_tree.selection()
        for i in sel:
            self.regles_tree.delete(i)

    def _add_format_row(self):
        self.formats_tree.insert("", tk.END, values=("ex: A_CLASSER", "{timestamp}_A_CLASSER_{original}.pdf"))

    def _remove_format_row(self):
        sel = self.formats_tree.selection()
        for i in sel:
            self.formats_tree.delete(i)

    def _add_fourn_row(self):
        self.fourn_tree.insert("", tk.END, values=("", ""))

    def _add_cle_row(self):
        """Ajoute une clé personnalisée (dialogue pour clé, description, valeur par défaut)."""
        cle = self._ask_edit_string("Nouvelle clé — nom de la clé", "", parent=self.root)
        if cle is None:
            return
        cle = cle.strip().replace(" ", "_")
        if not cle:
            return
        description = self._ask_edit_string("Nouvelle clé — description / utilité", "", parent=self.root) or ""
        valeur = self._ask_edit_string("Nouvelle clé — valeur par défaut", "", parent=self.root) or ""
        self.cles_tree.insert("", tk.END, values=(cle, description, valeur))

    def _remove_cle_row(self):
        sel = self.cles_tree.selection()
        for i in sel:
            self.cles_tree.delete(i)

    def _show_cles_help(self):
        """Affiche une fenêtre d'aide listant les clés utilisables et leur utilité."""
        win = tk.Toplevel(self.root)
        win.title("Aide — Clés utilisables dans les modèles")
        win.geometry("620x420")
        win.transient(self.root)
        f = ttk.Frame(win, padding=10)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text="Clés intégrées (toujours disponibles) :", font=("", 10, "bold")).pack(anchor=tk.W)
        text = tk.Text(f, wrap=tk.WORD, font=("Consolas", 9), height=10, state=tk.NORMAL)
        scroll = ttk.Scrollbar(f, orient=tk.VERTICAL, command=text.yview)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(4, 8))
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(4, 8))
        text.configure(yscrollcommand=scroll.set)
        for cle, desc in CLES_INTEGREES:
            text.insert(tk.END, f"  {{{cle}}}\n    → {desc}\n")
        custom = []
        for i in self.cles_tree.get_children():
            v = self.cles_tree.item(i, "values")
            if len(v) >= 3 and (v[0] or "").strip():
                custom.append((v[0].strip(), v[1].strip() or "(sans description)", v[2].strip()))
        if custom:
            text.insert(tk.END, "\nClés personnalisées (définies dans l'onglet Clés) :\n")
            for cle, desc, val in custom:
                text.insert(tk.END, f"  {{{cle}}}\n    → {desc}" + (f" (défaut: {val})" if val else "") + "\n")
        text.insert(tk.END, "\nUtilisation : dans les modèles de chemin ou de nom de fichier, écrivez {nom_cle} pour insérer la valeur (ex: Factures/{fournisseur}/{YYYY}/{MM}).\n")
        text.config(state=tk.DISABLED)
        ttk.Button(f, text="Fermer", command=win.destroy).pack(pady=(4, 0))

    def _add_fourn_row(self):
        self.fourn_tree.insert("", tk.END, values=("", ""))

    def _remove_fourn_row(self):
        sel = self.fourn_tree.selection()
        for i in sel:
            self.fourn_tree.delete(i)

    def _browse_config(self):
        p = filedialog.askopenfilename(
            title="Fichier de configuration",
            initialdir=str(PROJECT_ROOT),
            filetypes=[("YAML", "*.yaml *.yml"), ("Tous", "*.*")],
        )
        if p:
            self.var_config.set(p)
            self._load_config_ui()

    def _browse_inbox(self):
        p = filedialog.askdirectory(title="Dossier scanné (INBOX)", initialdir=self.var_inbox.get() or str(PROJECT_ROOT))
        if p:
            self.var_inbox.set(p)

    def _browse_racine(self):
        p = filedialog.askdirectory(title="Racine cible", initialdir=self.var_racine.get() or str(PROJECT_ROOT))
        if p:
            self.var_racine.set(p)

    def _load_config_ui(self):
        path = self.var_config.get().strip() or str(CONFIG_DEFAULT)
        path = Path(path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        self.config_path = path
        cfg = load_config_safe(path)
        if cfg is None:
            self.var_inbox.set("")
            self.var_racine.set("")
            self.label_inbox_status.config(text="Config introuvable ou invalide.")
            self.label_racine_status.config(text="Config introuvable ou invalide.")
            return
        self.config_data = cfg
        self.var_inbox.set(cfg.get("inbox", ""))
        self.var_racine.set(cfg.get("racine_destination", ""))
        for i in self.regles_tree.get_children():
            self.regles_tree.delete(i)
        regles = cfg.get("regles_classement") or []
        if not regles and (cfg.get("modele_chemin") or cfg.get("modele_nom_fichier")):
            regles = [{"type": "facture_fournisseur", "modele_chemin": cfg.get("modele_chemin", ""), "modele_nom_fichier": cfg.get("modele_nom_fichier", "")}]
        for r in regles:
            self.regles_tree.insert("", tk.END, values=(r.get("type", ""), r.get("modele_chemin", ""), r.get("modele_nom_fichier", "")))
        if not regles:
            self.regles_tree.insert("", tk.END, values=("facture_fournisseur", "Factures_fournisseurs/{fournisseur}/{YYYY}/{MM}", "{YYYY}-{MM}-{DD}_{type_doc}_{fournisseur}_{numero}.pdf"))
            self.regles_tree.insert("", tk.END, values=("défaut", "Divers/{YYYY}/{MM}", "{YYYY}-{MM}-{DD}_{type_doc}.pdf"))
        for i in self.formats_tree.get_children():
            self.formats_tree.delete(i)
        for motif, fmt in (cfg.get("formats_par_dossier") or {}).items():
            self.formats_tree.insert("", tk.END, values=(motif, fmt))
        for i in self.fourn_tree.get_children():
            self.fourn_tree.delete(i)
        for alias, nom in (cfg.get("mapping_fournisseurs") or {}).items():
            self.fourn_tree.insert("", tk.END, values=(alias, nom))
        for i in self.cles_tree.get_children():
            self.cles_tree.delete(i)
        for item in (cfg.get("cles_personnalisees") or []):
            if isinstance(item, dict):
                cle = item.get("cle", "").strip()
                if cle:
                    self.cles_tree.insert("", tk.END, values=(cle, item.get("description", ""), item.get("valeur_par_defaut", "")))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                cle = str(item[0]).strip()
                if cle:
                    self.cles_tree.insert("", tk.END, values=(cle, item[1] if len(item) > 2 else "", item[2] if len(item) > 2 else ""))
        self.label_inbox_status.config(text="Chargement du contenu INBOX…")
        self.label_racine_status.config(text="Chargement de l'arborescence…")
        threading.Thread(target=self._thread_load_inbox, daemon=True).start()
        threading.Thread(target=self._thread_load_racine, daemon=True).start()
        self.root.after(100, self._poll_queues)

    def _thread_load_inbox(self):
        inbox = self.var_inbox.get().strip()
        if not inbox or not Path(inbox).is_dir():
            self.inbox_queue.put(("done", [], None))
            return
        entries = list_dir_simple(inbox)
        self.inbox_queue.put(("done", entries, inbox))

    def _thread_load_racine(self):
        racine = self.var_racine.get().strip()
        if not racine or not Path(racine).is_dir():
            self.tree_queue.put(("done", [], None, {}))
            return
        try:
            entries, node_ids = build_tree_entries(racine)
            self.tree_queue.put(("done", entries, racine, node_ids))
        except Exception:
            self.tree_queue.put(("done", [], racine, {}))

    def _poll_queues(self):
        try:
            while True:
                msg = self.inbox_queue.get_nowait()
                if msg[0] == "done":
                    _, entries, path = msg
                    self._fill_inbox_tree(entries, path)
                break
        except queue.Empty:
            pass
        try:
            while True:
                msg = self.tree_queue.get_nowait()
                if msg[0] == "done":
                    _, entries, path, node_ids = msg if len(msg) == 4 else (msg[0], msg[1], msg[2], {})
                    self._fill_racine_tree(entries, path, node_ids)
                break
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queues)

    def _fill_inbox_tree(self, entries, path):
        for i in self.inbox_tree.get_children():
            self.inbox_tree.delete(i)
        if not path:
            self.label_inbox_status.config(text="Aucun dossier INBOX configuré.")
            return
        root_name = Path(path).name or path
        self.inbox_tree.insert("", "end", iid="inbox_root", text=root_name, values=(), open=True)
        for idx, (name, full_path, is_dir) in enumerate(entries):
            if name.startswith("..."):
                self.inbox_tree.insert("inbox_root", "end", iid=f"inbox_{idx}", text=name, values=())
                continue
            icon = "[D] " if is_dir else ""
            try:
                self.inbox_tree.insert("inbox_root", "end", iid=f"inbox_{idx}", text=f"{icon}{name}", values=(full_path,))
            except tk.TclError:
                pass
        self.label_inbox_status.config(text=f"Dossier scanné (INBOX) : {path} — {len(entries)} élément(s)")

    def _fill_racine_tree(self, entries, path, node_ids=None):
        for i in self.racine_tree.get_children():
            self.racine_tree.delete(i)
        if not path:
            self.label_racine_status.config(text="Aucune racine cible configurée.")
            return
        node_ids = node_ids or {}
        path = str(Path(path).resolve())
        root_name = Path(path).name or path
        self._racine_path_by_iid = {"0": path}
        self.racine_tree.insert("", "end", iid="0", text=root_name, values=(), open=True)
        # Construire map id -> (name, full_path, is_dir) pour chaque entrée
        by_id = {}
        for parent_id, name, full_path, is_dir, nid in entries:
            by_id[nid] = (parent_id, name, full_path, is_dir)
        # Map path -> id pour retrouver l'id à partir du chemin
        # Insérer dans l'ordre des ids pour que le parent soit toujours déjà présent
        for nid in sorted(by_id.keys(), key=lambda x: int(x) if x.isdigit() else 0):
            parent_id, name, full_path, is_dir = by_id[nid]
            self._racine_path_by_iid[nid] = full_path
            icon = "[D] " if is_dir else ""
            try:
                self.racine_tree.insert(parent_id, "end", iid=nid, text=f"{icon}{name}", values=(full_path,))
            except tk.TclError:
                pass
        total = len(entries) + 1
        self.label_racine_status.config(text=f"Racine cible : {path} — {total} nœud(s)")

    def _on_inbox_select(self, event):
        pass  # optionnel : afficher infos du fichier sélectionné

    def _on_racine_select(self, event):
        sel = self.racine_tree.selection()
        if not sel:
            return
        iid = sel[0]
        path = getattr(self, "_racine_path_by_iid", {}).get(iid)
        if not path:
            return
        p = Path(path)
        if not p.is_dir():
            self.file_list.delete(0, tk.END)
            self.file_list.insert(tk.END, p.name)
            self.label_file_status.config(text=f"Fichier : {path}")
            return
        self.label_file_status.config(text=f"Chargement de {path}…")
        files = list_dir_simple(path)
        self.file_list.delete(0, tk.END)
        for name, full_path, is_dir in files:
            prefix = "[D] " if is_dir else "    "
            self.file_list.insert(tk.END, f"{prefix}{name}")
        self.label_file_status.config(text=f"{path} — {len(files)} élément(s)")

    def _save_config(self):
        path = self.var_config.get().strip() or str(CONFIG_DEFAULT)
        path = Path(path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        cfg = dict(self.config_data) if self.config_data else {}
        cfg["inbox"] = self.var_inbox.get().strip()
        cfg["racine_destination"] = self.var_racine.get().strip()
        # A_CLASSER et FAILED toujours relatifs à la racine cible (celle configurée dans l'interface)
        cfg["dossier_a_classer"] = "A_CLASSER"
        cfg["dossier_failed"] = "FAILED"
        regles = []
        for i in self.regles_tree.get_children():
            v = self.regles_tree.item(i, "values")
            if len(v) >= 3 and (v[0].strip() or v[1].strip()):
                regles.append({"type": v[0].strip() or "défaut", "modele_chemin": v[1].strip(), "modele_nom_fichier": v[2].strip()})
        cfg["regles_classement"] = regles
        if regles:
            cfg["modele_chemin"] = regles[0].get("modele_chemin", "")
            cfg["modele_nom_fichier"] = regles[0].get("modele_nom_fichier", "")
        formats = {}
        for i in self.formats_tree.get_children():
            v = self.formats_tree.item(i, "values")
            if len(v) >= 2 and v[0].strip():
                formats[v[0].strip()] = v[1].strip()
        cfg["formats_par_dossier"] = formats
        mapping = {}
        for i in self.fourn_tree.get_children():
            v = self.fourn_tree.item(i, "values")
            if len(v) >= 2 and v[0].strip():
                mapping[v[0].strip()] = v[1].strip()
        cfg["mapping_fournisseurs"] = mapping
        cles_perso = []
        for i in self.cles_tree.get_children():
            v = self.cles_tree.item(i, "values")
            if len(v) >= 1 and (v[0] or "").strip():
                cles_perso.append({"cle": v[0].strip(), "description": (v[1] if len(v) > 1 else "").strip(), "valeur_par_defaut": (v[2] if len(v) > 2 else "").strip()})
        cfg["cles_personnalisees"] = cles_perso
        if save_config_safe(cfg, path):
            messagebox.showinfo("Sauvegarde", "Configuration enregistrée.", parent=self.root)
        else:
            messagebox.showerror("Erreur", "Impossible d'enregistrer la configuration.", parent=self.root)

    def _on_close(self):
        """Arrête la surveillance puis ferme la fenêtre."""
        if self._watcher_process is not None:
            try:
                self._watcher_process.terminate()
                self._watcher_process.wait(timeout=3)
            except Exception:
                try:
                    self._watcher_process.kill()
                except Exception:
                    pass
            self._watcher_process = None
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()


def main():
    os.chdir(PROJECT_ROOT)
    if not getattr(sys, "frozen", False) and str(PROJECT_ROOT / "src") not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
    app = ScannerGUI()
    app.run()


if __name__ == "__main__":
    main()
