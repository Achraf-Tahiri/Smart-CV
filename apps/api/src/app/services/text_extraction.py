"""Extraction de texte des documents (PDF, DOCX, images) — porté du POC.

- PDF : texte via pdfplumber ; si le texte est trop court (PDF scanné), bascule
  en OCR (rendu des pages via poppler puis Tesseract).
- DOCX : paragraphes via python-docx.
- Images : OCR Tesseract.

Fonctions **synchrones** (pdfplumber/pytesseract/pdf2image bloquent) : l'appelant
async doit les exécuter dans un thread (`anyio.to_thread`).
"""

import io
from pathlib import Path

import pdfplumber
import pytesseract
from docx import Document as DocxDocument
from pdf2image import convert_from_bytes
from PIL import Image

from app.core.config import settings

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}


class TextExtractionError(Exception):
    """Extraction de texte impossible (format non géré, fichier illisible)."""


def extract_text(data: bytes, *, filename: str) -> str:
    """Extrait le texte d'un document selon son extension. Lève `TextExtractionError`."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(data)
    if ext == ".docx":
        return _extract_docx(data)
    if ext in _IMAGE_EXTS:
        return _ocr_image(data)
    raise TextExtractionError(f"Extraction non supportée pour ce format : {ext or '(inconnu)'}")


def _extract_pdf(data: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = "\n".join((page.extract_text() or "") for page in pdf.pages).strip()
    except Exception as exc:  # pdf illisible / corrompu
        raise TextExtractionError(f"PDF illisible : {exc}") from exc

    # Peu ou pas de texte -> PDF probablement scanné -> OCR.
    if len(text) >= settings.ocr_min_chars:
        return text
    return _ocr_pdf(data)


def _ocr_pdf(data: bytes) -> str:
    try:
        images = convert_from_bytes(data, dpi=settings.ocr_dpi)
        return "\n".join(
            pytesseract.image_to_string(img, lang=settings.tesseract_lang) for img in images
        ).strip()
    except Exception as exc:
        raise TextExtractionError(f"OCR du PDF échoué : {exc}") from exc


def _ocr_image(data: bytes) -> str:
    try:
        with Image.open(io.BytesIO(data)) as image:
            return pytesseract.image_to_string(image, lang=settings.tesseract_lang).strip()
    except Exception as exc:
        raise TextExtractionError(f"OCR de l'image échoué : {exc}") from exc


def _extract_docx(data: bytes) -> str:
    try:
        document = DocxDocument(io.BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs).strip()
    except Exception as exc:
        raise TextExtractionError(f"DOCX illisible : {exc}") from exc
