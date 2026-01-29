# BASIC Scanner — Classement automatique de documents scannés

Outil **100 % local** pour **Windows et macOS** : surveillance d’un dossier INBOX (Scan to Folder), OCR, extraction des métadonnées (date, montant, fournisseur, etc.) et classement automatique selon des règles configurables (YAML). Aucun SaaS, aucune connexion Internet. *(Voir plus bas pour iOS et Android.)*

**Principe :** « Je scanne → ça se range tout seul. »
---

## Installation automatique (Windows)

### Installation graphique (interface visuelle)

Pour une **fenêtre logicielle** avec barre de progression et notification de fin (sans afficher le terminal) :

**Option 1 — Sans terminal (recommandé)**
- Double-cliquez sur **`install_gui.vbs`** à la racine du projet. Aucune fenêtre de commande ne s'affiche.

**Option 2 — Double-clic sur le .bat**
- Double-cliquez sur **`install_gui.bat`** (peut afficher brièvement une fenêtre de commande avant la fenêtre d'installation).

**Option 3 — Ligne de commande**
```powershell
python install_gui.py
```
(ou `py install_gui.py` si Python est lancé via le lanceur `py`.)

Une fenêtre s’ouvre avec :
- le titre **BASIC Scanner - Installation** ;
- l’étape en cours (texte) ;
- une **barre de progression** ;
- à la fin : **« Installation terminée »**, puis les boutons **Créer un raccourci sur le Bureau**, **Lancer l'interface maintenant** et **Fermer**.

Aucun terminal n’est affiché pendant l’installation. En cas d’erreur, une boîte de dialogue signale l’échec.
---

### Installation en ligne de commande (PowerShell)

Pour installer via un script PowerShell (sortie dans le terminal) :

**Option 1 — Double-clic**
- Double-cliquez sur `install.bat` à la racine du projet.

**Option 2 — PowerShell**
```powershell
.\install.ps1
```
Ou si l’exécution de scripts est restreinte :
```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

**Options du script**
- `-SkipVenv` : ne pas créer ni activer le venv (utilise le Python système).
- `-SkipTests` : ne pas lancer les tests après l’installation.
- `-NoDev` : installer sans les dépendances de dev (pytest, etc.).

Exemple :
```powershell
.\install.ps1 -SkipTests
```

Le script :
1. Vérifie la présence de **Python 3.11+**.
2. Crée l’environnement virtuel `.venv` s’il n’existe pas.
3. Installe les dépendances en mode éditable (`pip install -e ".[dev]"`).
4. Crée `config.yaml` à partir de `config.example.yaml` s’il n’existe pas.
5. Vérifie **Tesseract** et **Ghostscript** (affiche des instructions si absents).
6. Lance les tests (sauf si `-SkipTests` ou `-NoDev`).
---

## Vérification de l’installation

Pour **contrôler que l’installation s’est bien déroulée** (après `install.ps1` ou une installation manuelle) :

**Option 1 — Sans terminal**
- Double-cliquez sur **`verify.vbs`** : la vérification s'exécute en arrière-plan, un message indique succès ou échec (sans afficher le détail dans un terminal).

**Option 2 — Double-clic**
- Double-cliquez sur `verify.bat` (affiche un terminal avec le détail des contrôles).

**Option 3 — PowerShell**
```powershell
.\verify.ps1
```

Le script vérifie :
1. **Python 3.11+** (venv du projet prioritaire s’il existe).
2. **Package basic_scanner** : import et version.
3. **Commande CLI** : `basic_scanner --help` fonctionne.
4. **Configuration** : présence de `config.yaml`.
5. **Tests unitaires** : exécution de pytest (sauf avec `-Quick`).
6. **Prérequis OCR** : Tesseract et Ghostscript (informatifs, n’impactent pas le code de sortie).

**Code de sortie**
- **0** : tous les contrôles obligatoires sont OK (installation vérifiée).
- **1** : au moins un contrôle en échec (à corriger puis relancer `install.ps1` ou `verify.ps1`).

Exemple pour vérifier dans un script ou une CI :
```powershell
.\verify.ps1
if ($LASTEXITCODE -eq 0) { Write-Host "Installation OK" } else { exit 1 }
```

Vérification rapide (sans lancer les tests) :
```powershell
.\verify.ps1 -Quick
```
---

## Prérequis

- **Windows 10/11** ou **macOS** (Intel ou Apple Silicon)
- **Python 3.11+**
- **Tesseract OCR** (installé et accessible dans le `PATH`)
- **Ghostscript** (requis par `ocrmypdf`)

### Installation de Tesseract (Windows)

1. **Option A — Chocolatey**
   ```powershell
   choco install tesseract
   ```
2. **Option B — Installateur**
   - Télécharger : [GitHub - tesseract-ocr](https://github.com/UB-Mannheim/tesseract/wiki) ou [tesseract installer Windows](https://github.com/UB-Mannheim/tesseract/wiki)
   - Installer en cochant les langues **Français** et **English**
   - Ajouter le répertoire d’installation au `PATH` (ex. `C:\Program Files\Tesseract-OCR`)

Vérification :
```powershell
tesseract --version
```

### Installation de Ghostscript (pour ocrmypdf)

- Télécharger : [Ghostscript Windows](https://ghostscript.com/releases/gsdnld.html)
- Installer et ajouter au `PATH` si nécessaire.

Vérification :
```powershell
gswin64c -version
```

### Installation de Tesseract et Ghostscript (macOS)

Sur Mac (Homebrew) :
```bash
brew install tesseract tesseract-lang
brew install ghostscript
```

Vérification :
```bash
tesseract --version
gs --version
```
---

## Installation du projet (pip, manuelle)

À la racine du projet (ou utilisez l’**installation automatique** ci-dessus) :

```powershell
# Créer un environnement virtuel (recommandé)
python -m venv .venv
.venv\Scripts\activate

# Installation en mode éditable avec les dépendances
pip install -e ".[dev]"

# Ou sans les dépendances de dev (tests)
pip install -e .
```

Dépendances principales (déclarées dans `pyproject.toml`) :

- `watchdog` — surveillance du dossier INBOX  
- `ocrmypdf` — OCR PDF (Tesseract)  
- `pymupdf` (fitz) — lecture/écriture PDF  
- `rapidfuzz` — matching flou des fournisseurs  
- `pyyaml` — configuration  
---

## Distribution : exécutable (Windows et macOS)

Pour **distribuer l’application sans demander Python au client** : **un seul fichier** `.exe` à télécharger, sans dossier à copier.

### Construire l’exécutable

1. **Prérequis** : Python 3.11+ et les dépendances du projet installées (par ex. `pip install -e ".[dev]"` pour avoir PyInstaller).
2. À la racine du projet :
   ```batch
   build.bat
   ```
   Ou à la main :
   ```powershell
   pip install pyinstaller
   python -m PyInstaller --noconfirm basic_scanner.spec
   ```
3. **Résultat** : un seul fichier **`dist\BASIC Scanner.exe`** à distribuer (téléchargement, clé USB, etc.).

**Côté client (Windows)** : télécharger l'exe, le placer où l'on veut, double-cliquer. Au premier lancement la configuration est créée dans un dossier réservé (invisible). Configurer INBOX et racine puis « Lancer la surveillance ». Tesseract et Ghostscript doivent être installés sur la machine pour l'OCR des PDF scannés.

### macOS : application dans un dossier

**Sur Mac il n'y a pas de fichier .exe** — la version Windows (BASIC Scanner.exe) ne s'exécute pas sur Mac. La version Mac est un **dossier** nommé **BASIC Scanner** (ou un fichier **BASIC Scanner.zip** à décompresser pour obtenir ce dossier).

1. **Prérequis** : Mac avec Python 3.11+ et dépendances installées (`pip install -e ".[dev]"`).
2. À la racine du projet (sur Mac) :
   ```bash
   pip install pyinstaller
   python -m PyInstaller --noconfirm basic_scanner_mac.spec
   ```
3. **Résultat** : le dossier **`dist/BASIC Scanner/`** contient l'exécutable et les bibliothèques. Distribuer ce dossier (ou le zipper en `BASIC Scanner.zip`).

**Build Mac depuis Windows (sans avoir de Mac)** : le projet inclut un workflow **GitHub Actions** qui build la version Mac dans le cloud. Depuis Windows : 1) pousser le code sur GitHub (branch `main`) ; 2) aller dans **Actions** → workflow **Build macOS** → lancer **Run workflow** (ou attendre le build après un push) ; 3) à la fin du job, télécharger l’**artifact** **BASIC-Scanner-macOS** (fichier `BASIC-Scanner-macOS.zip`). Décompresser ce zip sur un Mac pour obtenir le dossier **BASIC Scanner** prêt à l’emploi.

**Côté client (macOS)** : il faut le **dossier** BASIC Scanner (ou BASIC Scanner.zip à décompresser). Si vous n'avez que **BASIC Scanner.exe**, c'est la version Windows — elle ne tourne pas sur Mac ; il faut récupérer la version Mac (dossier ou .zip). Une fois le dossier **BASIC Scanner** présent : lancer l'exécutable à l'intérieur (double-clic ou Terminal : `cd "BASIC Scanner"` puis `./"BASIC Scanner"`). Au premier lancement la configuration est créée dans `~/Library/Application Support/BASIC Scanner/`. Tesseract et Ghostscript doivent être installés (ex. `brew install tesseract ghostscript`).

**Si macOS affiche « The application can't be opened » (erreur -10661) ou si rien ne se passe au clic droit → Ouvrir** : l'app n'est pas signée et peut être bloquée ou plantée au lancement. Procédure recommandée :

1. **Retirer la quarantaine** (obligatoire après téléchargement) : ouvrir le **Terminal**, aller dans le dossier qui *contient* le dossier BASIC Scanner (ex. `cd ~/Downloads`), puis exécuter :  
   `xattr -cr "BASIC Scanner"`

2. **Lancer depuis le Terminal pour voir les erreurs** : aller *dans* le dossier BASIC Scanner et lancer l’exécutable :  
   `cd "BASIC Scanner"`  
   `./"BASIC Scanner"`  
   Si l’app plante ou n’affiche pas de fenêtre, le message d’erreur s’affichera dans le Terminal (ex. architecture Intel/Apple Silicon, bibliothèque manquante). Noter ce message pour diagnostiquer.

3. **Important** : il faut lancer l’**exécutable** à l’intérieur du dossier (nommé « BASIC Scanner », sans extension), pas le dossier lui‑même. Dans le Finder : ouvrir le dossier **BASIC Scanner**, puis double‑cliquer sur le fichier **BASIC Scanner** à l’intérieur.

Aucune installation de Python ni du code source côté client.
---


---


## iOS et Android (tablettes et téléphones)

BASIC Scanner est conçu pour **Windows et macOS** (ordinateur avec surveillance de dossier type « Scan to Folder »). Ce n'est pas une application mobile native.

**Pourquoi pas iOS/Android tels quels ?**
- L'application repose sur la **surveillance d'un dossier** (INBOX) et le déplacement de fichiers : flux typique « imprimante/MFP → dossier partagé → classement automatique ». Sur iOS et Android, il n'y a pas d'équivalent direct (pas de surveillance de dossier en arrière-plan comme sur desktop, accès fichiers restreint).
- Le code actuel (Python, tkinter, PyInstaller) cible le **desktop**. Pour tourner sur tablette/iOS/Android, il faudrait une **application mobile** (Swift/Kotlin, Flutter, React Native ou PWA) avec un usage différent (ex. importer un PDF, le classer, l'enregistrer ou l'envoyer).

**Pistes pour tablettes / mobiles :**
1. **Utiliser BASIC Scanner sur un Mac ou PC** qui partage le même INBOX (ex. dossier sur NAS) : les PDF scannés vers ce dossier sont traités par l'app sur le desktop ; la tablette peut servir à consulter ou déposer des fichiers sur le même partage.
2. **Évolution future** : une version « mobile » ou **web** (PWA) avec un workflow adapté (upload de PDF, classification, téléchargement ou envoi) serait un projet séparé (autre stack, autre UX).

---

## Configuration (dans l’interface, sans connaître le YAML)

Toute la configuration se fait **dans l’interface graphique** :

1. **Dossiers et arborescence** : dossier scanné (INBOX), racine cible, modèle d’arborescence (ex. `Factures_fournisseurs/{fournisseur}/{YYYY}/{MM}`) avec les mots possibles : `fournisseur`, `YYYY`, `MM`, `DD`, `numero`, `montant`, `type_doc`.
2. **Formats de fichier** : format de nom de fichier par défaut, et **format par dossier** (si le fichier va dans un dossier donné, utiliser un format de nom spécifique).
3. **Fournisseurs** : tableau alias → nom de dossier (pour le matching et l’arborescence).

Aucune édition manuelle du fichier YAML n’est nécessaire : « Charger la configuration » et « Sauvegarder la configuration » dans l’interface suffisent. Les chemins UNC (`\\NAS\Partage\...`) sont supportés.
---

## Interface graphique de visualisation

Une fenêtre permet de **visualiser et configurer** sans passer par le terminal :

- **Dossiers et arborescence** : INBOX, racine cible, modèle de chemin (tout configurable dans l’onglet).
- **Formats de fichier** : format par défaut et formats par dossier (tableau avec Ajouter/Supprimer). Double-clic sur une cellule pour modifier.
- **Mot-clés et identification de dossiers** : mapping alias → nom de dossier (tableau avec Ajouter/Supprimer). Double-clic sur une cellule pour modifier.
- **Visualisation** : contenu INBOX, arborescence de la racine cible, liste des fichiers du dossier sélectionné.

**Lancer l’interface (sans afficher le terminal)**

- **Double-clic** : `scan_gui.bat` ou `scan_gui.vbs` à la racine du projet (aucune fenêtre terminal).
- **Raccourci** : après l’installation graphique, un raccourci est proposé (Bureau sous Windows, Bureau ou menu applications sous Linux/Mac).

L’installation doit être faite au préalable (install_gui.bat ou install.ps1). Lors de l’installation graphique, il est proposé de **créer un raccourci** et de **lancer l’interface directement** à la fin.
---

## Utilisation

### Tri automatique : lancer la surveillance (obligatoire)

**Le tri automatique ne se fait que si la surveillance est en cours.** Lancer une fois (et laisser tourner) :

```powershell
basic_scanner run --config config.yaml
```

Ou avec un fichier de log :

```powershell
basic_scanner run --config config.yaml --log-file basic_scanner.log
```

L’application surveille l’INBOX, attend que chaque nouveau PDF soit « stable » (taille inchangée pendant `stability_seconds`), puis le traite (OCR si besoin, extraction, classement ou A_CLASSER/FAILED).

### Tester un seul fichier (sans déplacer)

```powershell
basic_scanner test-file "C:\Chemin\vers\document.pdf" --config config.yaml
```

Résultat affiché en JSON (extraction + destination prévue). Par défaut **dry-run** (aucun déplacement).

Pour effectuer le déplacement :

```powershell
basic_scanner test-file "C:\Chemin\vers\document.pdf" --config config.yaml --no-dry-run
```
---

## Comportement

- **Fichier stable** : taille inchangée pendant N secondes (évite de traiter un fichier encore en cours d’écriture par le MFP).
- **Doublons** : si le nom de fichier cible existe déjà, un suffixe `_1`, `_2`, … est ajouté.
- **A_CLASSER** : confidence &lt; seuil ou fournisseur inconnu → déplacement dans `A_CLASSER` avec nom du type `{timestamp}_A_CLASSER_{original}.pdf` et fichier `.json` des métadonnées à côté.
- **FAILED** : en cas d’exception non récupérable, le fichier est déplacé dans `FAILED` (jamais supprimé).
---

## Structure du projet

```
scanandorganize/
├── config.example.yaml
├── pyproject.toml
├── README.md
├── src/
│   └── basic_scanner/
│       ├── __init__.py
│       ├── main.py        # CLI (run, test-file)
│       ├── config.py      # Chargement YAML
│       ├── watcher.py     # Surveillance + file stability
│       ├── ocr.py         # OCR PDF scannés (ocrmypdf + fallback pytesseract sur images)
│       ├── extract.py     # Regex, extraction (date, montant, n° facture, etc.)
│       ├── classify.py   # Type doc + confidence
│       ├── suppliers.py  # Dictionnaire + rapidfuzz
│       ├── rules.py      # Chemin/nom, slugify
│       ├── mover.py      # Déplacement, A_CLASSER, FAILED
│       ├── models.py     # Dataclasses
│       └── logging_conf.py
└── tests/
    ├── test_extract.py
    ├── test_rules.py
    └── test_watcher_stability.py
```
---

## Tests

```powershell
# Depuis la racine du projet (avec venv activé)
pytest
# Avec couverture
pytest --cov=basic_scanner --cov-report=term-missing
```
---

## Packaging (prévu pour plus tard)

Le projet est structuré pour permettre ensuite :

- **Build .exe** : PyInstaller (`pyinstaller src/basic_scanner/main.py` ou spec dédié).
- **Installeur Windows** : Inno Setup ou équivalent, en incluant les prérequis (Tesseract, Ghostscript) ou en les documentant dans l’installeur.

Aucune dépendance réseau ; tout fonctionne en local (et sur chemins UNC).
