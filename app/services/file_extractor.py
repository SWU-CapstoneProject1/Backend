"""
업로드 파일에서 약관 본문 텍스트 추출
- PDF: PyMuPDF (fitz)
- 이미지(JPG/PNG): 미지원 (PaddleOCR 미설치)
"""
import re

import fitz  # PyMuPDF

MAX_PAGES = 100       # 최대 처리 페이지 수
MAX_TEXT_LENGTH = 50_000


def extract_text_from_pdf(content: bytes) -> str:
    """
    PDF 바이트를 받아 텍스트를 반환.
    실패 시 ValueError 발생.
    """
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception:
        raise ValueError("PDF 파일을 열 수 없습니다. 파일이 손상되었을 수 있습니다")

    if doc.page_count == 0:
        raise ValueError("PDF에 페이지가 없습니다")

    pages_text = []
    for page_num in range(min(doc.page_count, MAX_PAGES)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            pages_text.append(text)

    doc.close()

    if not pages_text:
        raise ValueError("PDF에서 텍스트를 추출하지 못했습니다. 스캔 이미지 PDF일 수 있습니다")

    raw = "\n\n".join(pages_text)
    raw = _clean_pdf_text(raw)

    if len(raw.strip()) < 50:
        raise ValueError("추출된 텍스트가 너무 짧습니다")

    return raw[:MAX_TEXT_LENGTH]


def extract_text_from_image(content: bytes, content_type: str) -> str:
    """
    이미지 OCR — 현재 미지원 (PaddleOCR 미설치).
    TODO: PaddleOCR 또는 Tesseract 연동 후 구현
    """
    raise NotImplementedError("이미지 파일 분석은 아직 지원하지 않습니다. PDF 파일을 업로드해주세요")


def extract_text_from_file(content: bytes, content_type: str) -> str:
    """content_type에 따라 적합한 추출기 호출"""
    if content_type == "application/pdf":
        return extract_text_from_pdf(content)
    elif content_type in {"image/jpeg", "image/png"}:
        return extract_text_from_image(content, content_type)
    else:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {content_type}")


def _clean_pdf_text(text: str) -> str:
    """PDF 추출 텍스트 후처리"""
    # 페이지 번호 패턴 제거 (- 1 -, 1 / 10 등)
    text = re.sub(r"(?m)^\s*-?\s*\d+\s*-?\s*$", "", text)
    text = re.sub(r"(?m)^\s*\d+\s*/\s*\d+\s*$", "", text)

    # 연속 공백 정리
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
