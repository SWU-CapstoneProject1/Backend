import re
from typing import List, Dict


ARTICLE_PATTERN = re.compile(
    r"(제\s*\d+\s*조(?:의\s*\d+)?\s*\[[^\]]*\]|제\s*\d+\s*조(?:의\s*\d+)?)"
)


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return text.strip()


def split_clauses(text: str) -> List[Dict]:
    """
    약관 전체 텍스트를 조항 단위로 분리
    1) 제N조 패턴 우선
    2) 없으면 문단 단위 fallback
    """
    text = normalize_text(text)
    if not text:
        return []

    matches = list(ARTICLE_PATTERN.finditer(text))

    clauses: List[Dict] = []

    if matches:
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            title = match.group(0).strip()
            content = text[start:end].strip()

            clauses.append({
                "clause_id": i + 1,
                "title": title,
                "content": content,
            })
        return clauses

    # fallback: 빈 줄 기준 문단 분리
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for i, paragraph in enumerate(paragraphs):
        clauses.append({
            "clause_id": i + 1,
            "title": f"문단 {i + 1}",
            "content": paragraph,
        })

    return clauses