import re
from typing import List, Dict


# 제N조 / 제N조의M / 제N조(제목) / 제N조[제목] 모두 인식
ARTICLE_PATTERN = re.compile(
    r"제\s*\d+\s*조(?:의\s*\d+)?"
    r"(?:\s*[\(\[（【][^\)\]）】]*[\)\]）】])?"
)

# 항·호 패턴: ① ② … / 가. 나. / 1) 2) / (1) (2)
SUB_PATTERN = re.compile(
    r"(?:^|\n)(?:[①②③④⑤⑥⑦⑧⑨⑩]|[가나다라마바사아자차카타파하]\.|[ⓐ-ⓩ]|\(\d+\)|\d+\))\s"
)

# 숫자+마침표 형식 조항 (1. 2. 형식 약관)
NUMBERED_PATTERN = re.compile(r"(?:^|\n)\d+\.\s+\S")

MIN_CLAUSE_LEN = 20   # 이보다 짧으면 앞 조항에 병합
MAX_CLAUSE_LEN = 1500  # 이보다 길면 항·호 기준으로 재분리


def normalize_text(text: str) -> str:
    if not text:
        return ""

    # 줄바꿈 통일
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 전각공백·non-breaking space → 일반 공백
    text = text.replace("\u3000", " ").replace("\xa0", " ")

    # PDF 복붙 잔재: 불릿 기호 앞뒤 공백 정리
    text = re.sub(r"\s*([●○◎▶▷■□※・])\s*", r" \1 ", text)

    # 탭 → 공백
    text = text.replace("\t", " ")

    # 같은 줄 연속 공백 → 단일 공백
    text = re.sub(r"[ ]{2,}", " ", text)

    # 줄 앞뒤 공백 제거
    text = re.sub(r" ?\n ?", "\n", text)

    # 3줄 이상 빈 줄 → 2줄로 축소
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 전각 숫자·문자 → 반각 (예: １ → 1)
    text = text.translate(str.maketrans(
        "０１２３４５６７８９ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ"
        "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ",
        "0123456789abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    ))

    return text.strip()


def _split_by_sub_items(content: str) -> List[str]:
    """항·호 패턴으로 긴 조항을 재분리"""
    parts = SUB_PATTERN.split(content)
    return [p.strip() for p in parts if p.strip()]


def split_clauses(text: str) -> List[Dict]:
    """
    약관 전체 텍스트를 조항 단위로 분리
    1) 제N조 패턴 우선
    2) 숫자+마침표 형식 fallback
    3) 빈 줄 기준 문단 fallback
    """
    text = normalize_text(text)
    if not text:
        return []

    matches = list(ARTICLE_PATTERN.finditer(text))

    # ── 1) 제N조 패턴 ───────────────────────────────
    if matches:
        clauses: List[Dict] = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            title = match.group(0).strip()
            content = text[start:end].strip()

            # 너무 짧으면 앞 조항에 병합
            if len(content) < MIN_CLAUSE_LEN and clauses:
                clauses[-1]["content"] += " " + content
                continue

            clauses.append({
                "clause_id": len(clauses) + 1,
                "title": title,
                "content": content,
            })
        return clauses

    # ── 2) 숫자+마침표 형식 fallback ─────────────────
    if NUMBERED_PATTERN.search(text):
        parts = NUMBERED_PATTERN.split(text)
        raw_titles = NUMBERED_PATTERN.findall(text)
        clauses = []
        for i, part in enumerate(parts[1:], start=0):
            content = (raw_titles[i].strip() + " " + part).strip() if i < len(raw_titles) else part.strip()
            if len(content) < MIN_CLAUSE_LEN and clauses:
                clauses[-1]["content"] += " " + content
                continue
            clauses.append({
                "clause_id": len(clauses) + 1,
                "title": f"조항 {len(clauses) + 1}",
                "content": content,
            })
        if clauses:
            return clauses

    # ── 3) 빈 줄 기준 문단 fallback ──────────────────
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    clauses = []
    for paragraph in paragraphs:
        # 너무 짧으면 앞 문단에 병합
        if len(paragraph) < MIN_CLAUSE_LEN and clauses:
            clauses[-1]["content"] += "\n" + paragraph
            continue

        # 너무 길면 항·호 기준으로 재분리
        if len(paragraph) > MAX_CLAUSE_LEN:
            sub_items = _split_by_sub_items(paragraph)
            for sub in sub_items:
                clauses.append({
                    "clause_id": len(clauses) + 1,
                    "title": f"문단 {len(clauses) + 1}",
                    "content": sub,
                })
            continue

        clauses.append({
            "clause_id": len(clauses) + 1,
            "title": f"문단 {len(clauses) + 1}",
            "content": paragraph,
        })

    return clauses
