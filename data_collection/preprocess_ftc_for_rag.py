import json
import re
from pathlib import Path
from typing import Any, Dict, List


INPUT_PATH = Path("data_collection/data/processed/ftc_details.json")
OUTPUT_JSONL_PATH = Path("data_collection/data/processed/rag_documents.jsonl")
OUTPUT_JSON_PATH = Path("data_collection/data/processed/rag_documents.json")
PREVIEW_JSON_PATH = Path("data_collection/data/processed/rag_preview.json")

# 법령 참조 패턴: (법 제3조), (제5조 제1항) 등
_LAW_REF = re.compile(r"[（\(][^）\)]*(?:법|조|항|호|규정|시행령)[^）\)]*[）\)]")

# 쪽수 표기: - 1 -, 제1쪽, 1/10 등
_PAGE_NUM = re.compile(r"(?:^|\n)\s*(?:-\s*\d+\s*-|제\s*\d+\s*쪽|\d+\s*/\s*\d+)\s*(?:\n|$)")

# HTML 태그
_HTML_TAG = re.compile(r"<[^>]+>")

# 연속 특수문자: ......  ------  ======
_REPEAT_PUNCT = re.compile(r"([.·\-=_]{3,})")

# 법령 상투어 (공백 포함 정규화)
_BOILERPLATE = re.compile(
    r"이하\s+[\""\"]?\w+[\""\"]?\s*(?:이|라)\s*한다"
    r"|이\s+사건\s+심결문\s*(?:은|의)"
    r"|공정거래위원회\s+의결\s+제\d+[-–]\d+호"
)


def clean_text(text: Any) -> str:
    if text is None:
        return ""

    text = str(text)

    # HTML 태그 제거
    text = _HTML_TAG.sub(" ", text)

    # 줄바꿈 통일
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 전각공백·NBSP·제로폭공백 → 일반 공백
    text = text.replace("\u3000", " ").replace("\xa0", " ").replace("\u200b", "")

    # 쪽수 표기 제거
    text = _PAGE_NUM.sub("\n", text)

    # 반복 특수문자 → 단일 공백
    text = _REPEAT_PUNCT.sub(" ", text)

    # 탭 → 공백
    text = text.replace("\t", " ")

    # 같은 줄 연속 공백
    text = re.sub(r"[ ]{2,}", " ", text)

    # 줄 앞뒤 공백
    text = re.sub(r" ?\n ?", "\n", text)

    # 3줄 이상 빈 줄 → 2줄
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_summary(text: Any) -> str:
    """summary 필드 전용 정제"""
    text = clean_text(text)
    if not text:
        return ""

    # 법령 참조 괄호 제거: (법 제3조 제1항) → 삭제
    text = _LAW_REF.sub("", text)

    # 상투어 제거
    text = _BOILERPLATE.sub("", text)

    # 중복 문장 제거 (마침표 기준 분리 후 dedup)
    sentences = [s.strip() for s in re.split(r"(?<=[.。])\s+", text) if s.strip()]
    seen: set = set()
    deduped = []
    for s in sentences:
        if s not in seen:
            seen.add(s)
            deduped.append(s)
    text = " ".join(deduped)

    # 공백 재정리
    text = re.sub(r"[ ]{2,}", " ", text)

    return text.strip()


def normalize_case_name(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def extract_text_fields(item: Dict[str, Any]) -> Dict[str, str]:
    case_id = clean_text(item.get("case_id", ""))
    case_name = normalize_case_name(item.get("case_name", ""))
    case_number = clean_text(item.get("case_number", ""))
    document_type = clean_text(item.get("document_type", ""))
    meeting_type = clean_text(item.get("meeting_type", ""))
    decision_number = clean_text(item.get("decision_number", ""))
    decision_date = clean_text(item.get("decision_date", ""))

    summary = clean_summary(item.get("summary", ""))
    order_text = clean_text(item.get("order_text", ""))
    reason_text = clean_text(item.get("reason_text", ""))
    full_text = clean_text(item.get("full_text", ""))

    return {
        "case_id": case_id,
        "case_name": case_name,
        "case_number": case_number,
        "document_type": document_type,
        "meeting_type": meeting_type,
        "decision_number": decision_number,
        "decision_date": decision_date,
        "summary": summary,
        "order_text": order_text,
        "reason_text": reason_text,
        "full_text": full_text,
    }


def build_rag_text(fields: Dict[str, str]) -> str:
    sections = []

    header_lines = []
    if fields["case_name"]:
        header_lines.append(f"사건명: {fields['case_name']}")
    if fields["case_number"]:
        header_lines.append(f"사건번호: {fields['case_number']}")
    if fields["decision_date"]:
        header_lines.append(f"결정일자: {fields['decision_date']}")
    if fields["decision_number"]:
        header_lines.append(f"결정번호: {fields['decision_number']}")
    if fields["document_type"]:
        header_lines.append(f"문서유형: {fields['document_type']}")
    if fields["meeting_type"]:
        header_lines.append(f"회의종류: {fields['meeting_type']}")

    if header_lines:
        sections.append("\n".join(header_lines))

    if fields["summary"]:
        sections.append(f"[결정요지]\n{fields['summary']}")
    if fields["order_text"]:
        sections.append(f"[주문]\n{fields['order_text']}")
    if fields["reason_text"]:
        sections.append(f"[이유]\n{fields['reason_text']}")
    if fields["full_text"]:
        sections.append(f"[본문]\n{fields['full_text']}")

    return "\n\n".join(section for section in sections if section.strip()).strip()


def choose_best_preview_text(fields: Dict[str, str], max_len: int = 500) -> str:
    """미리보기용 텍스트 — 문장 경계에서 자르기"""
    candidates = [
        fields["summary"],
        fields["reason_text"],
        fields["order_text"],
        fields["full_text"],
    ]

    for text in candidates:
        if not text:
            continue
        if len(text) <= max_len:
            return text

        # 문장 경계(마침표)에서 max_len 이내로 자르기
        cut = text[:max_len]
        last_period = max(cut.rfind("."), cut.rfind("。"), cut.rfind("다."))
        if last_period > max_len // 2:
            return cut[: last_period + 1].strip()
        return cut.strip() + "…"

    return ""


# ── 태그 키워드 맵 ───────────────────────────────────────────────────────────
# 각 태그: (필수 키워드 중 하나라도 포함, 우선순위 가중치)
_TAG_MAP: Dict[str, List[str]] = {
    "면책조항": ["면책", "책임을 지지 아니", "손해를 배상하지 아니", "면제", "책임 없음"],
    "계약해지": ["해지", "해제", "계약 종료", "일방 해지", "해약"],
    "자동갱신": ["자동 갱신", "자동갱신", "자동으로 연장", "갱신"],
    "과도한위약금": ["위약금", "손해배상 예정", "지체상금", "페널티"],
    "일방적변경": ["임의로 변경", "일방적으로 변경", "변경할 수 있다", "사전 통지 없이"],
    "소비자불리": ["고객의 책임", "회원의 책임", "이용자의 책임", "소비자 부담"],
    "거래상지위남용": ["거래상지위", "우월적 지위", "갑의 지위", "우월한 지위"],
    "부당광고": ["허위광고", "과장광고", "기만", "오인", "부당 표시"],
    "공동행위": ["공동행위", "담합", "입찰 담합", "가격 담합"],
    "가맹사업": ["가맹", "가맹점", "가맹본부", "프랜차이즈"],
    "개인정보": ["개인정보", "정보 제공", "제3자 제공", "마케팅 활용"],
    "재판관할": ["관할", "중재", "분쟁 해결", "소송 제기"],
}


def infer_unfair_clause_tags(text: str) -> List[str]:
    """키워드 기반 불공정 유형 태그 추론"""
    if not text:
        return []

    tags = []
    for tag, keywords in _TAG_MAP.items():
        if any(kw in text for kw in keywords):
            tags.append(tag)

    return sorted(set(tags))


def build_rag_document(item: Dict[str, Any]) -> Dict[str, Any]:
    fields = extract_text_fields(item)
    text = build_rag_text(fields)
    preview = choose_best_preview_text(fields)
    tags = infer_unfair_clause_tags(text)

    return {
        "id": fields["case_id"],
        "title": fields["case_name"],
        "text": text,
        "preview": preview,
        "metadata": {
            "case_id": fields["case_id"],
            "case_name": fields["case_name"],
            "case_number": fields["case_number"],
            "decision_date": fields["decision_date"],
            "decision_number": fields["decision_number"],
            "document_type": fields["document_type"],
            "meeting_type": fields["meeting_type"],
            "tags": tags,
            "source": "law.go.kr_ftc",
        },
    }


def validate_document(doc: Dict[str, Any]) -> bool:
    if not doc.get("id"):
        return False
    if not doc.get("title"):
        return False
    if not doc.get("text"):
        return False
    return True


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"입력 파일이 없습니다: {INPUT_PATH}\n"
            "먼저 collect_ftc_cases.py를 실행해서 ftc_details.json을 생성하세요."
        )

    raw_data = load_json(INPUT_PATH)

    if not isinstance(raw_data, list):
        raise ValueError(
            "ftc_details.json 형식이 예상과 다릅니다. 리스트 형태여야 합니다."
        )

    rag_documents: List[Dict[str, Any]] = []
    invalid_count = 0

    for item in raw_data:
        try:
            doc = build_rag_document(item)
            if validate_document(doc):
                rag_documents.append(doc)
            else:
                invalid_count += 1
        except Exception as e:
            invalid_count += 1
            print(f"[스킵] 문서 변환 실패: {e}")

    save_jsonl(OUTPUT_JSONL_PATH, rag_documents)
    save_json(OUTPUT_JSON_PATH, rag_documents)

    preview_data = [
        {
            "id": doc["id"],
            "title": doc["title"],
            "preview": doc["preview"],
            "metadata": doc["metadata"],
        }
        for doc in rag_documents[:5]
    ]
    save_json(PREVIEW_JSON_PATH, preview_data)

    print("전처리 완료")
    print(f"- 입력 문서 수: {len(raw_data)}")
    print(f"- 변환 성공 수: {len(rag_documents)}")
    print(f"- 스킵 수: {invalid_count}")
    print(f"- JSONL 저장: {OUTPUT_JSONL_PATH}")
    print(f"- JSON 저장: {OUTPUT_JSON_PATH}")
    print(f"- 미리보기 저장: {PREVIEW_JSON_PATH}")


if __name__ == "__main__":
    main()
