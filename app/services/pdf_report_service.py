"""
분석 결과 PDF 리포트 생성 서비스
PyMuPDF 내장 CJK 폰트 사용 (별도 폰트 파일 불필요)
"""
import io
from datetime import datetime
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from app.schemas.schemas import ResultResponse

# ── 색상 (RGB 0~1) ─────────────────────────────────────────────
COLOR_BLACK  = (0.1, 0.1, 0.1)
COLOR_GRAY   = (0.5, 0.5, 0.5)
COLOR_RED    = (0.85, 0.1, 0.1)
COLOR_ORANGE = (0.95, 0.5, 0.1)
COLOR_GREEN  = (0.1, 0.65, 0.3)
COLOR_BG_RED    = (1.0, 0.92, 0.92)
COLOR_BG_ORANGE = (1.0, 0.97, 0.88)
COLOR_BG_GREEN  = (0.92, 1.0, 0.94)

MARGIN   = 50
WIDTH    = 595   # A4
HEIGHT   = 842   # A4
LINE_H   = 18    # 기본 줄 간격
_FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/malgun.ttf"),                              # Windows
    Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),          # Linux (fonts-nanum)
    Path("/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf"),
]
FONT_FILE = next((f for f in _FONT_CANDIDATES if f.exists()), None)
FONT      = "malgun" if FONT_FILE else "helv"


def _font_kwargs():
    kwargs = {"fontname": FONT}
    if FONT_FILE:
        kwargs["fontfile"] = str(FONT_FILE)
    return kwargs


def _risk_color(risk_level: str):
    if risk_level == "danger":
        return COLOR_RED, COLOR_BG_RED, "위험"
    elif risk_level == "caution":
        return COLOR_ORANGE, COLOR_BG_ORANGE, "주의"
    return COLOR_GREEN, COLOR_BG_GREEN, "안전"


def _risk_grade(score: float) -> str:
    if score >= 61:
        return "위험"
    elif score >= 31:
        return "주의"
    return "안전"


class PDFWriter:
    """페이지 자동 추가 및 y 좌표 관리"""

    def __init__(self, doc: fitz.Document):
        self.doc = doc
        self.page = doc.new_page(width=WIDTH, height=HEIGHT)
        self.y = MARGIN

    def _new_page_if_needed(self, needed: float = 40):
        if self.y + needed > HEIGHT - MARGIN:
            self.page = self.doc.new_page(width=WIDTH, height=HEIGHT)
            self.y = MARGIN

    def _char_width(self, ch: str, size: int) -> float:
        cp = ord(ch)
        if 0xAC00 <= cp <= 0xD7A3 or 0x1100 <= cp <= 0x11FF or 0x3130 <= cp <= 0x318F:
            return size * 0.87  # 한글
        elif cp > 0x2E80:
            return size * 0.87  # 기타 CJK
        else:
            return size * 0.52  # ASCII/Latin

    def _wrap_lines(self, txt: str, x: int, size: int):
        max_width = WIDTH - MARGIN - x - 6
        result = []
        for para in txt.replace("\r\n", "\n").split("\n"):
            if not para:
                result.append("")
                continue
            current = ""
            current_w = 0.0
            for ch in para:
                cw = self._char_width(ch, size)
                if current_w + cw > max_width:
                    if current:
                        result.append(current)
                    current = ch
                    current_w = cw
                else:
                    current += ch
                    current_w += cw
            if current:
                result.append(current)
        return result

    def text(self, txt: str, x: int = MARGIN, size: int = 11,
             color=COLOR_BLACK, bold: bool = False):
        for line in self._wrap_lines(txt, x, size):
            self._new_page_if_needed(size + 6)
            self.page.insert_text((x, self.y), line, fontsize=size, color=color, **_font_kwargs())
            self.y += size + 6

    def gap(self, h: int = 10):
        self.y += h

    def line(self, color=COLOR_GRAY, width: float = 0.5):
        self._new_page_if_needed(10)
        self.page.draw_line(
            (MARGIN, self.y), (WIDTH - MARGIN, self.y),
            color=color, width=width,
        )
        self.y += 8

    def rect_text(self, txt: str, bg_color, text_color, size: int = 10):
        """배경색 박스 + 텍스트 (자동 줄바꿈)"""
        lines = self._wrap_lines(txt, MARGIN + 10, size)
        total_h = (size + 6) * len(lines) + 10
        self._new_page_if_needed(total_h)
        rect = fitz.Rect(MARGIN, self.y - 2, WIDTH - MARGIN, self.y + total_h)
        self.page.draw_rect(rect, color=None, fill=bg_color)
        for line in lines:
            self.page.insert_text((MARGIN + 10, self.y + size), line, fontsize=size, color=text_color, **_font_kwargs())
            self.y += size + 6
        self.y += 10

    def badge(self, label: str, color, x: int, y_offset: int = 0) -> int:
        """인라인 뱃지 — x 좌표 반환"""
        w = sum(self._char_width(ch, 9) for ch in label) + 10
        rect = fitz.Rect(x, self.y - 12 + y_offset, x + w, self.y + 2 + y_offset)
        self.page.draw_rect(rect, color=None, fill=color)
        self.page.insert_text(
            (x + 4, self.y + y_offset),
            label,
            fontsize=9,
            color=(1, 1, 1),
            **_font_kwargs(),
        )
        return x + w + 6


def _insert(w: "PDFWriter", x: float, text: str, size: int, color):
    w.text(text, x=int(x), size=size, color=color)


def _hline(w: "PDFWriter", color=COLOR_GRAY, lw: float = 0.5, gap_after: int = 16):
    w._new_page_if_needed(gap_after + 4)
    w.page.draw_line((MARGIN, w.y), (WIDTH - MARGIN, w.y), color=color, width=lw)
    w.y += gap_after


def generate_pdf_report(result: ResultResponse) -> bytes:
    """ResultResponse를 받아 PDF 바이트 반환"""
    doc = fitz.open()
    w = PDFWriter(doc)

    # ── 헤더 ─────────────────────────────────────────────────────
    _insert(w, MARGIN, "약간동의 분석 리포트", 20, (0.15, 0.35, 0.75))
    w.y += 4

    service = result.service_name or "미입력"
    now = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
    _insert(w, MARGIN, f"서비스명: {service}    분석 일시: {now}", 10, COLOR_GRAY)
    w.y += 6
    _hline(w, color=(0.15, 0.35, 0.75), lw=1.5, gap_after=18)

    # ── 종합 위험도 ───────────────────────────────────────────────
    score = result.risk_score or 0.0
    grade = _risk_grade(score)
    grade_color = COLOR_RED if grade == "위험" else (COLOR_ORANGE if grade == "주의" else COLOR_GREEN)

    _insert(w, MARGIN, "종합 위험도", 13, COLOR_BLACK)
    w.y += 2
    _insert(w, MARGIN, f"점수: {score:.1f}점    등급: {grade}", 12, grade_color)
    w.y += 2
    _insert(w, MARGIN,
            f"위험 {result.danger_count}건  |  주의 {result.caution_count}건  |  안전 {result.safe_count}건",
            10, COLOR_GRAY)
    w.y += 8
    _hline(w, gap_after=18)

    # ── 조항별 분석 ───────────────────────────────────────────────
    _insert(w, MARGIN, "조항별 분석 결과", 13, COLOR_BLACK)
    w.y += 8

    for clause in result.clauses:
        text_color, bg_color, label = _risk_color(clause.risk_level)

        w._new_page_if_needed(120)

        # 조항 번호 + 뱃지 (한 줄에)
        header = f"조항 {clause.index + 1}"
        w.page.insert_text((MARGIN, w.y), header, fontsize=11, color=COLOR_BLACK, **_font_kwargs())
        hdr_w = sum(w._char_width(ch, 11) for ch in header)
        bx = MARGIN + hdr_w + 10
        bw = sum(w._char_width(ch, 9) for ch in label) + 12
        w.page.draw_rect(fitz.Rect(bx, w.y - 10, bx + bw, w.y + 3), color=None, fill=text_color)
        w.page.insert_text((bx + 4, w.y), label, fontsize=9, color=(1, 1, 1), **_font_kwargs())
        w.y += 18

        # 원문 (배경색 박스)
        original = clause.original[:200] + ("..." if len(clause.original) > 200 else "")
        w.rect_text(original, bg_color, text_color, size=9)

        # 요약 (박스 완전히 벗어난 아래)
        if clause.summary:
            summary = clause.summary[:150] + ("..." if len(clause.summary) > 150 else "")
            w.y += 14
            _insert(w, MARGIN + 6, f"요약: {summary}", 9, COLOR_GRAY)

        w.y += 10
        _hline(w, color=(0.85, 0.85, 0.85), lw=0.3, gap_after=14)

    # ── 푸터 ──────────────────────────────────────────────────────
    w.y += 10
    _insert(w, MARGIN, "본 리포트는 AI 기반 자동 분석 결과로, 법적 효력이 없습니다.", 8, COLOR_GRAY)
    _insert(w, MARGIN, "약간동의 | yakgandongui.com", 8, COLOR_GRAY)

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()
