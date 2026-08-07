"""Tests d'extraction de texte (DOCX, PDF, OCR image).

L'OCR et le rendu PDF nécessitent Tesseract/poppler/police : présents dans
l'image de l'API (voir Dockerfile).
"""

import io

import pytest
from docx import Document as DocxDocument
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

from app.services.text_extraction import TextExtractionError, extract_text

_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _docx_bytes(text: str) -> bytes:
    doc = DocxDocument()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _pdf_bytes(text: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    pdf.multi_cell(0, 10, text)
    return bytes(pdf.output())


def _image_bytes(text: str) -> bytes:
    image = Image.new("RGB", (700, 140), "white")
    draw = ImageDraw.Draw(image)
    draw.text((10, 40), text, fill="black", font=ImageFont.truetype(_FONT, 48))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_extract_docx():
    text = extract_text(_docx_bytes("Alex Exemple\nDéveloppeur Python"), filename="cv.docx")
    assert "Alex Exemple" in text
    assert "Développeur Python" in text


def test_extract_pdf_text():
    content = "Ingenieur Informatique a Casablanca. Dix ans d experience Python et Django."
    text = extract_text(_pdf_bytes(content), filename="cv.pdf")
    assert "Informatique" in text
    assert "Django" in text


def test_ocr_image():
    text = extract_text(_image_bytes("INFORMATIQUE"), filename="scan.png")
    assert "INFORMATIQUE" in text.upper().replace(" ", "")


def test_unsupported_extension_raises():
    with pytest.raises(TextExtractionError):
        extract_text(b"data binaire", filename="ancien.doc")
