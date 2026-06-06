import re
from typing import Callable, Dict, List

from app.core.config import settings
from app.services.clause_splitter import split_clauses
from app.services.llm_explainer import generate_llm_explanation
from app.services.koelectra_classifier import classify_with_koelectra


RISK_RULES = [
    {
        "label": "면책 조항",
        "score": 3,
        "patterns": [
            r"책임\s*지지\s*않",
            r"책임을\s*지지\s*않",
            r"손해.*배상하지\s*않",
            r"면책",
        ],
        "reason": "사업자의 책임을 과도하게 면제할 가능성",
    },
    {
        "label": "일방적 변경",
        "score": 3,
        "patterns": [
            r"사전\s*통지\s*없이.*변경",
            r"일방적으로.*변경",
            r"임의로.*변경",
        ],
        "reason": "사업자가 약관을 일방적으로 변경할 가능성",
    },
    {
        "label": "계약 해지",
        "score": 2,
        "patterns": [
            r"해지할\s*수\s*있",
            r"즉시.*해지",
            r"계약.*종료할\s*수\s*있",
        ],
        "reason": "사업자에게 과도한 해지 권한 부여",
    },
    {
        "label": "환불 제한",
        "score": 3,
        "patterns": [
            r"환불.*불가",
            r"환불되지\s*않",
            r"어떠한\s*경우에도.*환불",
        ],
        "reason": "소비자의 환불 권리를 과도하게 제한",
    },
    {
        "label": "자동 갱신",
        "score": 2,
        "patterns": [
            r"자동\s*갱신",
        ],
        "reason": "이용자 동의 없이 계약 연장 가능성",
    },
    {
        "label": "과도한 위약금",
        "score": 2,
        "patterns": [
            r"위약금",
            r"손해배상\s*예정",
        ],
        "reason": "소비자에게 과도한 금전적 부담",
    },
]


def split_sentences(text: str) -> List[str]:
    sentences = re.split(r"[.\n]", text)
    return [s.strip() for s in sentences if s.strip()]


def classify_clause_risk_by_rules(clause_text: str) -> Dict:
    sentences = split_sentences(clause_text)

    total_score = 0
    matched_rules = set()
    risk_types = set()

    for sentence in sentences:
        for rule in RISK_RULES:
            for pattern in rule["patterns"]:
                if re.search(pattern, sentence):
                    total_score += rule["score"]
                    matched_rules.add(rule["reason"])
                    risk_types.add(rule["label"])
                    break

    if total_score >= 5:
        risk_level = "HIGH"
    elif total_score >= 2:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "risk_level": risk_level,
        "risk_score": total_score,
        "risk_types": sorted(list(risk_types)),
        "matched_rules": sorted(list(matched_rules)),
    }


def classify_clause_risk(clause_text: str) -> Dict:
    model_result = classify_with_koelectra(clause_text)
    if model_result is not None:
        return model_result
    return classify_clause_risk_by_rules(clause_text)


def rerank_cases(clause_text: str, cases: List[Dict]) -> List[Dict]:
    keywords = ["책임", "손해", "환불", "해지", "면책", "위약금", "계약", "개인정보", "변경"]

    reranked = []

    for case in cases:
        bonus = 0.0
        haystack = f"{case.get('title', '')} {case.get('preview', '')} {' '.join(case.get('metadata', {}).get('tags', []))}"

        for keyword in keywords:
            if keyword in clause_text and keyword in haystack:
                bonus += 0.1

        final_score = case["score"] + bonus
        new_case = dict(case)
        new_case["reranked_score"] = round(final_score, 4)
        reranked.append(new_case)

    reranked.sort(key=lambda x: x["reranked_score"], reverse=True)
    return reranked[:3]


def filter_cases_by_similarity(cases: List[Dict], min_similarity: float | None = None) -> List[Dict]:
    threshold = settings.PRECEDENT_MIN_SIMILARITY if min_similarity is None else min_similarity
    if threshold <= 0:
        return cases

    filtered = []
    for case in cases:
        score = case.get("reranked_score", case.get("score", 0.0))
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.0
        if score >= threshold:
            filtered.append(case)
    return filtered


def _get_retriever():
    from app.services.precedent_retriever import FTCRetriever

    return FTCRetriever()


def _notify_progress(progress_callback: Callable[..., None] | None, **payload) -> None:
    if progress_callback is not None:
        progress_callback(**payload)


def _clause_preview(text: str, limit: int = 140) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def _clause_percent(index: int, total: int, step_ratio: float) -> int:
    if total <= 0:
        return 15
    per_clause = 75 / total
    return min(90, int(15 + (index - 1) * per_clause + per_clause * step_ratio))


def analyze_terms_text(terms_text: str, progress_callback: Callable[..., None] | None = None) -> Dict:
    _notify_progress(
        progress_callback,
        progress_percent=5,
        stage="preparing",
        message="분석 모델과 판례 데이터를 준비하고 있습니다.",
    )
    retriever = _get_retriever()
    _notify_progress(
        progress_callback,
        progress_percent=10,
        stage="splitting",
        message="약관 조항을 분리하고 있습니다.",
    )
    clauses = split_clauses(terms_text)
    total = len(clauses)
    _notify_progress(
        progress_callback,
        progress_percent=15,
        stage="clauses_ready",
        message=f"총 {total}개 조항을 찾았습니다.",
        current_clause=0,
        total_clauses=total,
        current_clause_title="",
        current_clause_preview="",
    )

    analyzed = []
    stats = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for index, clause in enumerate(clauses, start=1):
        text = clause["content"]
        title = clause.get("title", "")
        preview = _clause_preview(text)

        _notify_progress(
            progress_callback,
            progress_percent=_clause_percent(index, total, 0.0),
            stage="classifying",
            message=f"{index}/{total}번 조항의 위험도를 분류하고 있습니다.",
            current_clause=index,
            total_clauses=total,
            current_clause_title=title,
            current_clause_preview=preview,
        )
        risk = classify_clause_risk(text)
        stats[risk["risk_level"]] += 1

        _notify_progress(
            progress_callback,
            progress_percent=_clause_percent(index, total, 0.35),
            stage="retrieving_precedents",
            message=f"{index}/{total}번 조항과 관련된 판례를 찾고 있습니다.",
            current_clause=index,
            total_clauses=total,
            current_clause_title=title,
            current_clause_preview=preview,
        )
        if risk["risk_level"] == "LOW":
            retrieved = retriever.search(text, top_k=3)
        else:
            retrieved = retriever.search(text, top_k=8)

        reranked = filter_cases_by_similarity(rerank_cases(text, retrieved))

        _notify_progress(
            progress_callback,
            progress_percent=_clause_percent(index, total, 0.65),
            stage="generating_explanation",
            message=f"{index}/{total}번 조항의 AI 설명을 생성하고 있습니다.",
            current_clause=index,
            total_clauses=total,
            current_clause_title=title,
            current_clause_preview=preview,
        )
        llm_result = generate_llm_explanation(
            clause_text=text,
            risk_result=risk,
            precedent_cases=reranked,
        )

        analyzed.append({
            "clause_id": clause["clause_id"],
            "title": clause["title"],
            "content": text,
            "risk_level": risk["risk_level"],
            "risk_score": risk["risk_score"],
            "risk_types": risk["risk_types"],
            "matched_rules": risk["matched_rules"],
            "llm_summary": llm_result.get("summary", ""),
            "plain_explanation": llm_result.get("plain_explanation", ""),
            "legal_rationale": llm_result.get("legal_rationale", ""),
            "consumer_warning": llm_result.get("consumer_warning", ""),
            "confidence_note": llm_result.get("confidence_note", ""),
            "precedent_cases": [
                {
                    "id": c["id"],
                    "title": c["title"],
                    "score": c["reranked_score"],
                    "decision_date": c["metadata"].get("decision_date", ""),
                    "case_number": c["metadata"].get("case_number", ""),
                    "tags": c["metadata"].get("tags", []),
                    "preview": c["preview"],
                }
                for c in reranked
            ],
        })
        _notify_progress(
            progress_callback,
            progress_percent=_clause_percent(index, total, 1.0),
            stage="clause_completed",
            message=f"{index}/{total}번 조항 분석을 완료했습니다.",
            current_clause=index,
            total_clauses=total,
            current_clause_title=title,
            current_clause_preview=preview,
        )

    _notify_progress(
        progress_callback,
        progress_percent=92,
        stage="summarizing",
        message="전체 위험도 요약을 계산하고 있습니다.",
        current_clause=total,
        total_clauses=total,
        current_clause_title="",
        current_clause_preview="",
    )
    # 가중치 방식: 위험×3 + 주의×1 / 전체×3 × 100
    weighted = stats["HIGH"] * 3 + stats["MEDIUM"] * 1
    risk_score = round(weighted / (total * 3) * 100, 1) if total > 0 else 0.0

    if risk_score >= 61:
        risk_grade = "위험"
    elif risk_score >= 31:
        risk_grade = "주의"
    else:
        risk_grade = "안전"

    return {
        "summary": {
            "total_clauses": total,
            "high_risk": stats["HIGH"],
            "medium_risk": stats["MEDIUM"],
            "low_risk": stats["LOW"],
            "overall_risk_ratio": round(risk_score / 100, 2),
            "risk_score": risk_score,
            "risk_grade": risk_grade,
        },
        "clauses": analyzed,
    }
