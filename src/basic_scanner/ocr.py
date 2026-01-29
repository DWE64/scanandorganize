"""
OCR local pour PDF scannés (contenant des images).
- Lecture du texte dans les images des pages via Tesseract (ocrmypdf ou pytesseract).
- Les PDF issus d'un scan n'ont en général pas de couche texte : on déclenche l'OCR
  dès que peu de texte est extrait, puis fallback sur reconnaissance directe des images.
"""
from pathlib import Path
from typing import Optional

from basic_scanner.logging_conf import get_logger

logger = get_logger("ocr")

# Seuil en caractères : en dessous, on considère que le PDF est image-only (scan) et on lance l'OCR
MIN_TEXT_LENGTH_FOR_OCR = 30

_OCRMYPDF_AVAILABLE: Optional[bool] = None
_PYTESSERACT_AVAILABLE: Optional[bool] = None


def _check_ocrmypdf() -> bool:
    global _OCRMYPDF_AVAILABLE
    if _OCRMYPDF_AVAILABLE is not None:
        return _OCRMYPDF_AVAILABLE
    try:
        import ocrmypdf  # noqa: F401
        _OCRMYPDF_AVAILABLE = True
    except ImportError:
        _OCRMYPDF_AVAILABLE = False
    return _OCRMYPDF_AVAILABLE


def _check_pytesseract() -> bool:
    global _PYTESSERACT_AVAILABLE
    if _PYTESSERACT_AVAILABLE is not None:
        return _PYTESSERACT_AVAILABLE
    try:
        import pytesseract  # noqa: F401
        _PYTESSERACT_AVAILABLE = True
    except ImportError:
        _PYTESSERACT_AVAILABLE = False
    return _PYTESSERACT_AVAILABLE


def _extract_text_from_pdf_images(pdf_path: Path, lang: str = "fra+eng") -> str:
    """
    Fallback OCR : rend chaque page du PDF en image puis reconnaît le texte avec Tesseract (pytesseract).
    Utilisé quand ocrmypdf n'est pas disponible ou a échoué.
    Les PDF scannés contiennent des images ; cette méthode lit le texte dans ces images.
    """
    if not _check_pytesseract():
        logger.warning("pytesseract non disponible; impossible d'extraire le texte des images.")
        return ""

    import fitz  # PyMuPDF

    doc = fitz.open(str(pdf_path))
    text_parts = []
    try:
        for i, page in enumerate(doc):
            # Rendre la page en image (matrice de pixels) pour Tesseract
            pix = page.get_pixmap(alpha=False, dpi=150)
            if pix.width == 0 or pix.height == 0:
                continue
            try:
                from PIL import Image
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            except ImportError:
                logger.warning("PIL/Pillow non disponible pour le fallback OCR.")
                break
            try:
                import pytesseract
                # Tesseract accepte plusieurs langues avec + (ex: fra+eng)
                page_text = pytesseract.image_to_string(img, lang=lang)
                if page_text and page_text.strip():
                    text_parts.append(page_text.strip())
            except Exception as e:
                logger.debug("OCR page %s: %s", i + 1, e)
    finally:
        doc.close()

    result = "\n".join(text_parts).strip()
    if result:
        logger.info("OCR fallback (images des pages) : %s caractères extraits pour %s", len(result), pdf_path.name)
    return result


def ensure_pdf_has_text(pdf_path: Path, lang: str = "fra+eng") -> Path:
    """
    S'assure que le PDF contient une couche texte (OCR si nécessaire).
    Modifie le fichier sur place ou crée une copie temporaire selon ocrmypdf.
    :param pdf_path: Chemin du PDF.
    :param lang: Langues Tesseract (ex: fra+eng).
    :return: Chemin du PDF avec texte (même fichier si déjà du texte, sinon OCRisé).
    """
    if not _check_ocrmypdf():
        logger.warning("ocrmypdf non disponible; extraction texte sans OCR (peut être vide).")
        return pdf_path

    try:
        import ocrmypdf
        # ocrmypdf peut modifier in-place ou nécessiter output différent
        # On utilise un fichier temporaire puis replace pour éviter lock
        output = pdf_path.parent / (pdf_path.stem + "_ocr.pdf")
        ocrmypdf.ocr(str(pdf_path), str(output), language=lang, skip_text=True)
        # Remplacer l'original par la version OCR pour la suite
        output.replace(pdf_path)
        logger.info("OCR appliqué: %s", pdf_path.name)
        return pdf_path
    except Exception as e:
        logger.error("Échec OCR %s: %s", pdf_path, e)
        # On continue avec le PDF tel quel (extraction peut être vide)
        return pdf_path


def extract_text_from_pdf(pdf_path: Path, lang: str = "fra+eng") -> str:
    """
    Extrait tout le texte du PDF. Pour les PDF scannés (images sans couche texte),
    déclenche l'OCR : d'abord ocrmypdf (ajout d'une couche texte), puis en fallback
    lecture directe des images de chaque page avec Tesseract (pytesseract).
    :param pdf_path: Chemin du PDF.
    :param lang: Langues Tesseract (ex: fra+eng).
    :return: Texte complet (concaténation des pages).
    """
    import fitz  # PyMuPDF

    path = Path(pdf_path)
    if not path.is_file():
        return ""

    # 1) Extraire le texte de la couche PDF (vide pour un scan pur)
    doc = fitz.open(str(path))
    text_parts = []
    try:
        for page in doc:
            text_parts.append(page.get_text())
        full_text = "\n".join(text_parts).strip()
    finally:
        doc.close()

    # 2) PDF scanné = peu ou pas de texte → reconnaissance du texte dans les images
    if len(full_text) < MIN_TEXT_LENGTH_FOR_OCR:
        # 2a) ocrmypdf : ajoute une couche texte au PDF puis on ré-extraît
        ensure_pdf_has_text(path, lang=lang)
        doc = fitz.open(str(path))
        try:
            text_parts = [page.get_text() for page in doc]
            full_text = "\n".join(text_parts).strip()
        finally:
            doc.close()

        # 2b) Si toujours insuffisant (ocrmypdf indisponible ou échec), fallback : lire les images des pages
        if len(full_text) < MIN_TEXT_LENGTH_FOR_OCR:
            fallback_text = _extract_text_from_pdf_images(path, lang=lang)
            if len(fallback_text) > len(full_text):
                full_text = fallback_text

    return full_text
