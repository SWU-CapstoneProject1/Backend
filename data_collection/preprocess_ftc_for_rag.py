import json
import re
from pathlib import Path
from typing import Any, Dict, List


INPUT_PATH = Path("data_collection/data/processed/ftc_details.json")
OUTPUT_JSONL_PATH = Path("data_collection/data/processed/rag_documents.jsonl")
OUTPUT_JSON_PATH = Path("data_collection/data/processed/rag_documents.json")
PREVIEW_JSON_PATH = Path("data_collection/data/processed/rag_preview.json")


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


def clean_text(text: Any) -> str:
    if text is None:
        return ""

    text = str(text)

    # 줄바꿈/공백 정리
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)

    # 특수 공백 정리
    text = text.replace("\u00a0", " ").replace("\u200b", "")

    return text.strip()


def normalize_case_name(text: str) -> str:
    text = clean_text(text)
    # 불필요하게 띄어진 글자 조금 보정
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def extract_text_fields(item: Dict[str, Any]) -> Dict[str, str]:
    """
    collect_ftc_cases.py에서 만든 정규화 결과를 기준으로 텍스트 필드 추출
    """
    case_id = clean_text(item.get("case_id", ""))
    case_name = normalize_case_name(item.get("case_name", ""))
    case_number = clean_text(item.get("case_number", ""))
    document_type = clean_text(item.get("document_type", ""))
    meeting_type = clean_text(item.get("meeting_type", ""))
    decision_number = clean_text(item.get("decision_number", ""))
    decision_date = clean_text(item.get("decision_date", ""))

    summary = clean_text(item.get("summary", ""))
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
    """
    검색과 생성에 모두 도움이 되도록 문서 텍스트를 구성
    """
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
    """
    미리보기용 짧은 텍스트
    """
    candidates = [
        fields["summary"],
        fields["reason_text"],
        fields["order_text"],
        fields["full_text"],
    ]

    for text in candidates:
        if text:
            text = text[:max_len].strip()
            return text

    return ""


def infer_unfair_clause_tags(text: str) -> List[str]:
    """
    아주 단순한 초기 태깅
    이후 고도화 가능
    """
    tags = []
    lowered = text.lower()

    keyword_map = {
        "면책": ["면책", "책임을 지지 아니", "손해를 배상하지 아니"],
        "계약해지": ["해지", "해제", "계약 종료"],
        "자동갱신": ["자동 갱신", "자동갱신", "갱신"],
        "과도한위약금": ["위약금", "손해배상 예정"],
        "일방적변경": ["일방", "임의로 변경", "변경할 수 있다"],
        "소비자불리": ["고객의 책임", "회원의 책임", "소비자"],
        "거래상지위남용": ["거래상지위", "우월적 지위"],
        "부당광고": ["광고", "표시", "기만", "오인"],
        "공동행위": ["공동행위", "담합", "입찰"],
        "가맹사업": ["가맹", "가맹점", "가맹본부"],
    }

    for tag, keywords in keyword_map.items():
        if any(keyword in text or keyword in lowered for keyword in keywords):
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

    preview_data = []
    for doc in rag_documents[:5]:
        preview_data.append({
            "id": doc["id"],
            "title": doc["title"],
            "preview": doc["preview"],
            "metadata": doc["metadata"],
        })

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