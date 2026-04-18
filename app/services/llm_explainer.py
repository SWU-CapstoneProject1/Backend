import json
import os
from typing import Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def build_prompt(
    clause_text: str,
    risk_result: Dict,
    precedent_cases: List[Dict],
) -> str:
    case_lines = []

    for idx, case in enumerate(precedent_cases, start=1):
        case_lines.append(
            f"{idx}. 사건명: {case.get('title', '')}\n"
            f"   사건번호: {case.get('metadata', {}).get('case_number', '')}\n"
            f"   결정일자: {case.get('metadata', {}).get('decision_date', '')}\n"
            f"   태그: {', '.join(case.get('metadata', {}).get('tags', []))}\n"
            f"   미리보기: {case.get('preview', '')[:300]}"
        )

    cases_text = "\n".join(case_lines) if case_lines else "관련 심결례 없음"

    return f"""
너는 소비자가 이해하기 쉽게 약관을 설명하는 법률 AI 도우미다.

아래 조항을 분석해서 JSON만 출력해라.
반드시 쉬운 한국어로 작성해라.
근거가 약하면 과장하지 말고 신중하게 표현해라.

[입력 조항]
{clause_text}

[위험도 분석 결과]
- risk_level: {risk_result.get("risk_level")}
- risk_score: {risk_result.get("risk_score")}
- risk_types: {", ".join(risk_result.get("risk_types", []))}
- matched_rules: {", ".join(risk_result.get("matched_rules", []))}

[유사 공정위 심결례]
{cases_text}

[출력 형식]
다음 JSON 형식만 출력:
{{
  "summary": "한 줄 요약",
  "plain_explanation": "일반 사용자가 이해할 수 있는 쉬운 설명",
  "legal_rationale": "왜 문제될 수 있는지 근거 중심 설명",
  "consumer_warning": "소비자가 주의할 점",
  "confidence_note": "판단의 한계 또는 주의사항"
}}
""".strip()


def call_claude_json(prompt: str) -> Optional[Dict]:
    if not ANTHROPIC_API_KEY:
        return None

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-3-5-sonnet-latest",
        "max_tokens": 800,
        "temperature": 0.2,
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        text = data["content"][0]["text"].strip()
        text = text.removeprefix("```json").removesuffix("```").strip()

        return json.loads(text)
    except Exception:
        return None


def generate_llm_explanation(
    clause_text: str,
    risk_result: Dict,
    precedent_cases: List[Dict],
) -> Dict:
    prompt = build_prompt(clause_text, risk_result, precedent_cases)
    result = call_claude_json(prompt)

    if result:
        return result

    risk_level = risk_result.get("risk_level", "LOW")
    risk_types = risk_result.get("risk_types", [])

    if risk_level == "HIGH":
        summary = "불공정 가능성이 높은 조항입니다."
    elif risk_level == "MEDIUM":
        summary = "주의가 필요한 조항입니다."
    else:
        summary = "현재 기준으로는 위험도가 낮은 조항입니다."

    type_text = ", ".join(risk_types) if risk_types else "명확한 위험 유형 없음"

    return {
        "summary": summary,
        "plain_explanation": f"이 조항은 {type_text} 관점에서 검토가 필요합니다.",
        "legal_rationale": "사업자에게 과도하게 유리하거나 소비자 권리를 제한하는 표현이 있는지 확인해야 합니다.",
        "consumer_warning": "환불, 해지, 책임 제한, 일방적 변경 조항은 특히 주의해서 확인하세요.",
        "confidence_note": "현재 설명은 규칙 기반 분석과 검색된 심결례를 바탕으로 생성되었습니다.",
    }