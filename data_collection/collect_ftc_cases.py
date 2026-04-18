import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, parse_qs

import requests
from dotenv import load_dotenv

load_dotenv()

LAW_API_KEY = os.getenv("LAW_API_KEY")

BASE_SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
BASE_DETAIL_URL = "https://www.law.go.kr/DRF/lawService.do"

TARGET = "ftc"
OUTPUT_TYPE = "XML"

REQUEST_TIMEOUT = 30
SLEEP_SECONDS = 0.3

RAW_DIR = Path("data_collection/data/raw/ftc")
PROCESSED_DIR = Path("data_collection/data/processed")

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def ensure_api_key() -> None:
    if not LAW_API_KEY:
        raise ValueError("LAW_API_KEY 없음 (.env 확인)")


def request_xml(url: str, params: dict) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
    res.raise_for_status()

    text = res.text.strip()

    if "<html" in text.lower()[:300]:
        raise Exception(f"HTML 응답 반환\nURL: {res.url}\n{text[:500]}")

    return text


def parse_xml(xml_text: str) -> Dict[str, Any]:
    root = ET.fromstring(xml_text)

    def convert(elem: ET.Element):
        children = list(elem)
        if not children:
            return (elem.text or "").strip()

        data = {}
        for c in children:
            value = convert(c)
            if c.tag in data:
                if isinstance(data[c.tag], list):
                    data[c.tag].append(value)
                else:
                    data[c.tag] = [data[c.tag], value]
            else:
                data[c.tag] = value
        return data

    return {root.tag: convert(root)}


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def pick_first(item: dict, keys: List[str]) -> str:
    for key in keys:
        val = item.get(key)
        if val not in (None, ""):
            return str(val).strip()
    return ""


def extract_id_from_link(link: str) -> str:
    if not link:
        return ""
    try:
        parsed = urlparse(link)
        qs = parse_qs(parsed.query)
        return qs.get("ID", [""])[0]
    except Exception:
        return ""


def fetch_ftc_case_list(page: int = 1, display: int = 20, query: str | None = None) -> Dict[str, Any]:
    ensure_api_key()

    params = {
        "OC": LAW_API_KEY,
        "target": TARGET,
        "type": OUTPUT_TYPE,
        "page": page,
        "display": display,
        "sort": "ddes",
        "search": 1,
    }

    if query:
        params["query"] = query

    xml_text = request_xml(BASE_SEARCH_URL, params)
    parsed = parse_xml(xml_text)

    save_json(RAW_DIR / f"list_page_{page}.json", parsed)
    return parsed


def extract_list_items(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    root = list(parsed.values())[0]

    if isinstance(root, dict):
        for v in root.values():
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
            if isinstance(v, dict):
                return [v]

    return []


def normalize_case_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    detail_link = pick_first(item, [
        "결정문상세링크",
        "상세링크",
        "판례상세링크",
        "링크",
    ])

    case_id = pick_first(item, [
        "결정문일련번호",
        "일련번호",
        "ID",
        "id",
        "판례일련번호",
        "문서일련번호",
    ])

    if not case_id:
        case_id = extract_id_from_link(detail_link)

    return {
        "case_id": case_id,
        "case_name": pick_first(item, ["사건명", "제목"]),
        "case_number": pick_first(item, ["사건번호"]),
        "document_type": pick_first(item, ["문서유형"]),
        "meeting_type": pick_first(item, ["회의종류"]),
        "decision_number": pick_first(item, ["결정번호"]),
        "decision_date": pick_first(item, ["결정일자"]),
        "detail_link": detail_link,
        "raw": item,
    }


def fetch_ftc_case_detail(case_id: str) -> Dict[str, Any]:
    ensure_api_key()

    params = {
        "OC": LAW_API_KEY,
        "target": TARGET,
        "type": OUTPUT_TYPE,
        "ID": case_id,
    }

    xml_text = request_xml(BASE_DETAIL_URL, params)
    parsed = parse_xml(xml_text)

    save_json(RAW_DIR / f"detail_{case_id}.json", parsed)
    return parsed


def normalize_case_detail(parsed: Dict[str, Any], case_id: str) -> Dict[str, Any]:
    root = list(parsed.values())[0]

    if not isinstance(root, dict):
        return {
            "case_id": case_id,
            "raw": parsed,
        }

    return {
        "case_id": pick_first(root, ["결정문일련번호", "일련번호", "ID"]) or case_id,
        "case_name": pick_first(root, ["사건명", "제목"]),
        "case_number": pick_first(root, ["사건번호"]),
        "document_type": pick_first(root, ["문서유형"]),
        "meeting_type": pick_first(root, ["회의종류"]),
        "decision_number": pick_first(root, ["결정번호"]),
        "decision_date": pick_first(root, ["결정일자"]),
        "summary": pick_first(root, ["결정요지", "요지"]),
        "order_text": pick_first(root, ["주문"]),
        "reason_text": pick_first(root, ["이유"]),
        "full_text": pick_first(root, ["의결문", "본문"]),
        "raw": parsed,
    }


def collect_ftc_cases(page: int = 1, display: int = 20, query: str | None = None) -> Dict[str, int]:
    summaries: List[Dict[str, Any]] = []
    details: List[Dict[str, Any]] = []

    parsed = fetch_ftc_case_list(page=page, display=display, query=query)
    items = extract_list_items(parsed)

    print(f"[목록] {len(items)}개")

    if not items:
        save_json(PROCESSED_DIR / "ftc_summaries.json", summaries)
        save_json(PROCESSED_DIR / "ftc_details.json", details)
        return {"summary_count": 0, "detail_count": 0}

    print("\n[디버그] 첫 raw item")
    print(json.dumps(items[0], ensure_ascii=False, indent=2))

    normalized = [normalize_case_summary(i) for i in items]

    print("\n[디버그] 첫 normalized item")
    print(json.dumps(normalized[0], ensure_ascii=False, indent=2))

    for item in normalized:
        case_id = item["case_id"]
        print(f"\n[ID 확인] {case_id} | {item['case_name']}")

        if not case_id:
            print("ID 없음 → 스킵")
            continue

        summaries.append(item)

        try:
            detail_raw = fetch_ftc_case_detail(case_id)
            detail_normalized = normalize_case_detail(detail_raw, case_id)
            details.append(detail_normalized)
            print("상세 수집 성공")
            time.sleep(SLEEP_SECONDS)
        except Exception as e:
            print(f"상세 실패: {e}")

    save_json(PROCESSED_DIR / "ftc_summaries.json", summaries)
    save_json(PROCESSED_DIR / "ftc_details.json", details)

    with open(PROCESSED_DIR / "ftc_summaries.jsonl", "w", encoding="utf-8") as f:
        for item in summaries:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(PROCESSED_DIR / "ftc_details.jsonl", "w", encoding="utf-8") as f:
        for item in details:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    return {
        "summary_count": len(summaries),
        "detail_count": len(details),
    }


if __name__ == "__main__":
    result = collect_ftc_cases(page=1, display=20, query=None)

    print("\n===== 최종 결과 =====")
    print(json.dumps(result, ensure_ascii=False, indent=2))