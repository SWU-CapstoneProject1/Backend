from __future__ import annotations

import re
import shutil
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings

MAX_PAGES = 100
MAX_TEXT_LENGTH = 50_000
MAX_IMAGE_PIXELS = 40_000_000

SUPPORTED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
}


class OcrUnavailableError(RuntimeError):
    """Raised when OCR is enabled in code but the local OCR engine is missing."""


def extract_text_from_pdf(content: bytes) -> str:
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError("PDF 파일을 열 수 없습니다. 파일이 손상되었는지 확인해주세요.") from exc

    try:
        if doc.page_count == 0:
            raise ValueError("PDF에 페이지가 없습니다.")

        raw = _extract_text_from_pdf_pages(doc)
        if len(raw.strip()) >= 50:
            return raw[:MAX_TEXT_LENGTH]

        ocr_text = _extract_text_from_scanned_pdf(doc)
        if _is_ocr_text_usable(ocr_text, min_length=50):
            return ocr_text[:MAX_TEXT_LENGTH]
    finally:
        doc.close()

    if raw.strip():
        raise ValueError("PDF에서 추출된 텍스트가 너무 짧습니다.")
    raise ValueError("PDF에서 분석 가능한 약관 텍스트를 충분히 추출하지 못했습니다.")


def extract_text_from_image(content: bytes, content_type: str) -> str:
    if content_type not in SUPPORTED_IMAGE_CONTENT_TYPES:
        raise ValueError(f"지원하지 않는 이미지 형식입니다: {content_type}")

    image = _open_image(content)
    image = _prepare_image_for_ocr(image)
    raw = _run_tesseract_ocr(image)
    text = _clean_text(raw)

    min_length = max(10, getattr(settings, "OCR_MIN_TEXT_LENGTH", 20))
    if not _is_ocr_text_usable(text, min_length=min_length):
        raise ValueError("이미지에서 분석 가능한 약관 텍스트를 충분히 추출하지 못했습니다.")

    return text[:MAX_TEXT_LENGTH]


def extract_text_from_file(content: bytes, content_type: str) -> str:
    normalized_content_type = (content_type or "").lower()
    if normalized_content_type == "application/pdf":
        return extract_text_from_pdf(content)
    if normalized_content_type in SUPPORTED_IMAGE_CONTENT_TYPES:
        return extract_text_from_image(content, normalized_content_type)
    raise ValueError(f"지원하지 않는 파일 형식입니다: {content_type}")


def _is_ocr_text_usable(text: str, min_length: int) -> bool:
    normalized = text.strip()
    if len(normalized) < min_length:
        return False

    readable_chars = re.findall(r"[가-힣A-Za-z]", normalized)
    return len(readable_chars) >= min(10, min_length)


def _extract_text_from_pdf_pages(doc: fitz.Document) -> str:
    pages_text: list[str] = []
    for page_num in range(min(doc.page_count, MAX_PAGES)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            pages_text.append(text)
    return _clean_text("\n\n".join(pages_text))


def _extract_text_from_scanned_pdf(doc: fitz.Document) -> str:
    page_limit = min(
        doc.page_count,
        MAX_PAGES,
        max(1, getattr(settings, "OCR_PDF_MAX_PAGES", 20)),
    )
    dpi = min(300, max(72, getattr(settings, "OCR_PDF_DPI", 200)))
    matrix = fitz.Matrix(dpi / 72, dpi / 72)

    pages_text: list[str] = []
    for page_num in range(page_limit):
        page = doc[page_num]
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        with Image.open(BytesIO(pixmap.tobytes("png"))) as img:
            img.load()
            image = img.convert("RGB")

        image = _prepare_image_for_ocr(image)
        text = _run_tesseract_ocr(image)
        if text.strip():
            pages_text.append(text)

    return _clean_text("\n\n".join(pages_text))


def _open_image(content: bytes) -> Image.Image:
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

    try:
        with Image.open(BytesIO(content)) as img:
            img.load()
            image = ImageOps.exif_transpose(img)
            width, height = image.size
            if width * height > MAX_IMAGE_PIXELS:
                raise ValueError("이미지 해상도가 너무 큽니다.")
            return image.convert("RGB")
    except ValueError:
        raise
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("이미지 파일을 열 수 없습니다. PNG 또는 JPG 파일인지 확인해주세요.") from exc


def _prepare_image_for_ocr(image: Image.Image) -> Image.Image:
    width, height = image.size
    shortest_side = min(width, height)

    if shortest_side < 1200:
        scale = min(3.0, 1200 / max(shortest_side, 1))
        image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

    grayscale = ImageOps.grayscale(image)
    return ImageOps.autocontrast(grayscale)


def _run_tesseract_ocr(image: Image.Image) -> str:
    pytesseract = _load_pytesseract()
    cmd = _resolve_tesseract_cmd()
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd

    language = getattr(settings, "OCR_LANGUAGE", "kor+eng") or "kor+eng"
    psm = getattr(settings, "OCR_PSM", 6)
    config = f"--oem 3 --psm {psm}"
    tessdata_dir = _resolve_tessdata_dir()
    if tessdata_dir:
        config = f"{config} --tessdata-dir {tessdata_dir}"

    try:
        return pytesseract.image_to_string(image, lang=language, config=config)
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrUnavailableError(_missing_tesseract_message()) from exc
    except pytesseract.TesseractError as exc:
        message = str(exc)
        if "Failed loading language" in message or "Error opening data file" in message:
            raise OcrUnavailableError(
                f"Tesseract OCR 언어 데이터가 없습니다. OCR_LANGUAGE={language!r}에 필요한 traineddata를 설치해주세요."
            ) from exc
        raise ValueError(f"OCR 처리 중 오류가 발생했습니다: {message}") from exc
    except UnicodeDecodeError as exc:
        raise OcrUnavailableError(
            "Tesseract OCR 언어 데이터 로딩 중 오류가 발생했습니다. kor.traineddata와 함께 필요한 보조 traineddata가 "
            "TESSDATA_DIR에 있는지 확인해주세요."
        ) from exc


def _load_pytesseract() -> Any:
    try:
        import pytesseract
    except ImportError as exc:
        raise OcrUnavailableError(
            "pytesseract 패키지가 설치되어 있지 않습니다. `pip install -r requirements.txt`를 실행해주세요."
        ) from exc
    return pytesseract


def _resolve_tesseract_cmd() -> str | None:
    configured = getattr(settings, "TESSERACT_CMD", "") or ""
    if configured:
        configured_path = Path(configured)
        if configured_path.exists():
            return str(configured_path)
        found = shutil.which(configured)
        if found:
            return found
        raise OcrUnavailableError(f"TESSERACT_CMD 경로를 찾을 수 없습니다: {configured}")

    found = shutil.which("tesseract")
    if found:
        return found

    for candidate in (
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
    ):
        if candidate.exists():
            return str(candidate)

    raise OcrUnavailableError(_missing_tesseract_message())


def _resolve_tessdata_dir() -> str | None:
    configured = getattr(settings, "TESSDATA_DIR", "") or ""
    if not configured:
        return None

    path = Path(configured)
    if not path.exists():
        raise OcrUnavailableError(f"TESSDATA_DIR 경로를 찾을 수 없습니다: {path}")
    return str(path)


def _missing_tesseract_message() -> str:
    return (
        "Tesseract OCR 실행 파일을 찾을 수 없습니다. Windows에 Tesseract OCR과 Korean language data를 설치한 뒤 "
        "`.env`에 `TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe`를 설정해주세요."
    )


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
    text = re.sub(r"(?m)^\s*-?\s*\d+\s*-?\s*$", "", text)
    text = re.sub(r"(?m)^\s*\d+\s*/\s*\d+\s*$", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
