import unittest
from io import BytesIO
from unittest.mock import patch

import fitz
from PIL import Image

from app.services import file_extractor


def _blank_pdf_bytes() -> bytes:
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    data = doc.write()
    doc.close()
    return data


def _png_bytes() -> bytes:
    image = Image.new("RGB", (600, 300), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class FileExtractorOcrTests(unittest.TestCase):
    def test_scanned_pdf_falls_back_to_ocr(self):
        ocr_text = "약관 OCR 추출 결과입니다. " * 5

        with patch.object(file_extractor, "_extract_text_from_scanned_pdf", return_value=ocr_text) as ocr:
            extracted = file_extractor.extract_text_from_pdf(_blank_pdf_bytes())

        self.assertIn("약관 OCR 추출 결과", extracted)
        ocr.assert_called_once()

    def test_image_ocr_rejects_too_short_text(self):
        with patch.object(file_extractor, "_run_tesseract_ocr", return_value="짧음"):
            with self.assertRaises(ValueError):
                file_extractor.extract_text_from_image(_png_bytes(), "image/png")

    def test_image_ocr_rejects_numeric_garbage_text(self):
        garbage = "212 222 222\n222 222 222 222 2222"

        with patch.object(file_extractor, "_run_tesseract_ocr", return_value=garbage):
            with self.assertRaises(ValueError):
                file_extractor.extract_text_from_image(_png_bytes(), "image/png")


if __name__ == "__main__":
    unittest.main()
