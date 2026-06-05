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

    def _wrap_lines(self, txt: str, x: int, size: int):
        max_chars = max(1, int((WIDTH - MARGIN - x) / (size * 0.85)))
        result = []
        for para in txt.replace("\r\n", "\n").split("\n"):
            if not para:
                result.append("")
                continue
            while len(para) > max_chars:
                result.append(para[:max_chars])
                para = para[max_chars:]
            result.append(para)
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
        lines = self._wrap_lines(txt, MARGIN + 6, size)
        total_h = (size + 6) * len(lines) + 8
        self._new_page_if_needed(total_h)
        rect = fitz.Rect(MARGIN, self.y - 2, WIDTH - MARGIN, self.y + total_h)
        self.page.draw_rect(rect, color=None, fill=bg_color)
        for line in lines:
            self.page.insert_text((MARGIN + 6, self.y + size), line, fontsize=size, color=text_color, **_font_kwargs())
            self.y += size + 6
        self.y += 8

    def badge(self, label: str, color, x: int, y_offset: int = 0) -> int:
        """인라인 뱃지 — x 좌표 반환"""
        w = len(label) * 7 + 10
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


def generate_pdf_report(result: ResultResponse) -> bytes:
    """ResultResponse를 받아 PDF 바이트 반환"""
    doc = fitz.open()
    w = PDFWriter(doc)

    # ── 헤더 ────────────────────────────────────────────────────
    w.text("약간동의 분석 리포트", size=20, color=(0.15, 0.35, 0.75))
    w.gap(4)

    service = result.service_name or "미입력"
    now = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
    w.text(f"서비스명: {service}    분석 일시: {now}", size=10, color=COLOR_GRAY)
    w.gap(6)
    w.line(color=(0.15, 0.35, 0.75), width=1.5)

    # ── 위험도 요약 ──────────────────────────────────────────────
    score = result.risk_score or 0.0
    grade = _risk_grade(score)
    grade_color = COLOR_RED if grade == "위험" else (COLOR_ORANGE if grade == "주의" else COLOR_GREEN)

    w.text("종합 위험도", size=13, color=COLOR_BLACK)
    w.gap(2)
    w.text(f"점수: {score:.1f}점    등급: {grade}", size=12, color=grade_color)
    w.gap(4)
    w.text(
        f"위험 {result.danger_count}건  |  주의 {result.caution_count}건  |  안전 {result.safe_count}건",
        size=10, color=COLOR_GRAY,
    )
    w.gap(8)
    w.line()

    # ── 조항별 분석 ──────────────────────────────────────────────
    w.text("조항별 분석 결과", size=13, color=COLOR_BLACK)
    w.gap(6)

    for clause in result.clauses:
        text_color, bg_color, label = _risk_color(clause.risk_level)

        # 조항 번호 + 뱃지
        w._new_page_if_needed(80)
        header = f"조항 {clause.index + 1}"
        w.text(header, size=11, color=COLOR_BLACK)
        # 뱃지 (같은 줄에 그리기 위해 y를 되돌림)
        badge_y = w.y - (11 + 6)
        badge_x = MARGIN + len(header) * 8 + 4
        rect = fitz.Rect(badge_x, badge_y - 2, badge_x + 36, badge_y + 12)
        w.page.draw_rect(rect, color=None, fill=text_color)
        w.page.insert_text((badge_x + 4, badge_y + 9), label, fontsize=9, color=(1, 1, 1), **_font_kwargs())

        # 원문 (배경색 박스)
        original = clause.original[:200] + ("..." if len(clause.original) > 200 else "")
        w.rect_text(original, bg_color, text_color, size=9)

        # 요약
        if clause.summary:
            summary = clause.summary[:150] + ("..." if len(clause.summary) > 150 else "")
            w.text(f"요약: {summary}", size=9, color=COLOR_GRAY, x=MARGIN + 10)

        w.gap(10)
        w.line(color=(0.85, 0.85, 0.85), width=0.3)

    # ── 푸터 ─────────────────────────────────────────────────────
    w.gap(16)
    w.text("본 리포트는 AI 기반 자동 분석 결과로, 법적 효력이 없습니다.", size=8, color=COLOR_GRAY)
    w.text("약간동의 | yakgandongui.com", size=8, color=COLOR_GRAY)

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()
