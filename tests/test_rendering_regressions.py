"""Pixel and document-integrity checks using generated PDFs only."""
import fitz
import numpy as np
from PySide6.QtCore import QRect

from darkmode import apply_dark_mode
from renderer import PDFRenderer
from utils.image_utils import get_qimage
from viewer import ViewerController


def make_pdf(path, image_rect):
    doc = fitz.open()
    page = doc.new_page(width=100, height=100)
    pixels = bytes([200, 30, 10]) * 400
    image = fitz.Pixmap(fitz.csRGB, 20, 20, pixels, False)
    page.insert_image(fitz.Rect(image_rect), stream=image.tobytes("png"))
    doc.save(path)
    doc.close()


def pixel(image, x, y):
    return image.pixelColor(x, y).getRgb()[:3]


def test_rgb_and_rgba_inversion_and_alpha():
    rgba = np.array([[[255, 0, 10, 37], [0, 255, 255, 200]]], dtype=np.uint8)
    result = apply_dark_mode(rgba, True)
    assert result.tolist() == [[[0, 255, 245, 37], [255, 0, 0, 200]]]
    rgb = np.array([[[255, 0, 10]]], dtype=np.uint8)
    assert apply_dark_mode(rgb, False).tolist() == [[[0, 255, 245]]]


def test_embedded_image_preserved_in_actual_render_at_zoom(tmp_path):
    path = tmp_path / "embedded.pdf"
    make_pdf(str(path), (20, 20, 40, 40))
    renderer = PDFRenderer()
    assert renderer.load_document(str(path))
    for zoom in (1, 2):
        pix = renderer.get_page_pixmap(0, zoom)
        bboxes = renderer.get_page_image_bboxes(0, zoom)
        image = get_qimage(pix, True, bboxes)
        assert (image.width(), image.height()) == (100 * zoom, 100 * zoom)
        assert pixel(image, 5 * zoom, 5 * zoom) == (0, 0, 0)
        assert pixel(image, 30 * zoom, 30 * zoom) == (200, 30, 10)
    renderer.close_document()


def test_full_page_image_is_inverted_in_actual_render(tmp_path):
    path = tmp_path / "scan.pdf"
    make_pdf(str(path), (0, 0, 100, 100))
    renderer = PDFRenderer()
    assert renderer.load_document(str(path))
    pix = renderer.get_page_pixmap(0)
    image = get_qimage(pix, True, renderer.get_page_image_bboxes(0))
    assert pixel(image, 50, 50) == (55, 225, 245)
    renderer.close_document()


def test_undo_preserves_nonhighlight_annotations(temp_pdf, qapp):
    doc = fitz.open(temp_pdf)
    page = doc[0]
    note = page.add_text_annot((60, 60), "original note")
    note.update()
    doc.saveIncr()
    doc.close()
    viewer = ViewerController()
    viewer.open_document(temp_pdf)
    viewer.add_highlight(QRect(50, 50, 200, 30))
    assert viewer.undo()
    page = viewer.renderer.doc[0]
    assert [(a.type[0], a.info["content"]) for a in page.annots()] == [(fitz.PDF_ANNOT_TEXT, "original note")]
    viewer.renderer.close_document()
    with fitz.open(temp_pdf) as reopened:
        page = reopened[0]
        assert [(a.type[0], a.info["content"]) for a in page.annots()] == [(fitz.PDF_ANNOT_TEXT, "original note")]


def test_eraser_preserves_nonhighlight_annotations(temp_pdf, qapp):
    doc = fitz.open(temp_pdf)
    page = doc[0]
    note = page.add_text_annot((60, 60), "original note")
    note.update()
    doc.saveIncr()
    doc.close()
    viewer = ViewerController()
    viewer.open_document(temp_pdf)
    viewer.erase_highlight(QRect(0, 0, 300, 300))
    page = viewer.renderer.doc[0]
    assert [(a.type[0], a.info["content"]) for a in page.annots()] == [(fitz.PDF_ANNOT_TEXT, "original note")]
    viewer.renderer.close_document()
    with fitz.open(temp_pdf) as reopened:
        page = reopened[0]
        assert [(a.type[0], a.info["content"]) for a in page.annots()] == [(fitz.PDF_ANNOT_TEXT, "original note")]


def test_invalid_pdf_is_rejected(tmp_path):
    path = tmp_path / "damaged.pdf"
    path.write_bytes(b"%PDF-1.7\ninvalid document contents")
    renderer = PDFRenderer()
    assert renderer.load_document(str(path)) is False
    assert renderer.get_page_count() == 0


def test_highlight_and_erase_are_saved_to_generated_pdf(temp_pdf, qapp):
    viewer = ViewerController()
    viewer.open_document(temp_pdf)
    viewer.add_highlight(QRect(50, 50, 200, 30))
    viewer.renderer.close_document()
    doc = fitz.open(temp_pdf)
    assert len(list(doc[0].annots())) == 1
    doc.close()
    viewer.open_document(temp_pdf)
    viewer.erase_highlight(QRect(0, 0, 300, 300))
    viewer.renderer.close_document()
    doc = fitz.open(temp_pdf)
    assert len(list(doc[0].annots())) == 0
    doc.close()
