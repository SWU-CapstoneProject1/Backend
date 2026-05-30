import logging
from functools import lru_cache
from typing import Any, Dict, Optional

from app.core.config import settings


logger = logging.getLogger(__name__)


_DEFAULT_LABEL_MAP = {
    "LABEL_0": "LOW",
    "LABEL_1": "MEDIUM",
    "LABEL_2": "HIGH",
}

_CANONICAL_LABELS = {
    "HIGH": "HIGH",
    "HIGH_RISK": "HIGH",
    "DANGER": "HIGH",
    "DANGEROUS": "HIGH",
    "RISK": "HIGH",
    "위험": "HIGH",
    "MEDIUM": "MEDIUM",
    "MEDIUM_RISK": "MEDIUM",
    "CAUTION": "MEDIUM",
    "WARNING": "MEDIUM",
    "주의": "MEDIUM",
    "LOW": "LOW",
    "LOW_RISK": "LOW",
    "SAFE": "LOW",
    "NORMAL": "LOW",
    "안전": "LOW",
}

_RISK_SCORE_BY_LEVEL = {
    "HIGH": 5,
    "MEDIUM": 2,
    "LOW": 0,
}


def _normalize_label_key(label: str) -> str:
    return label.strip().upper().replace("-", "_").replace(" ", "_")


def _parse_label_map(raw_map: str) -> Dict[str, str]:
    parsed = dict(_DEFAULT_LABEL_MAP)

    for item in raw_map.split(","):
        if ":" not in item:
            continue
        raw_label, risk_level = item.split(":", 1)
        normalized_level = _CANONICAL_LABELS.get(_normalize_label_key(risk_level))
        if normalized_level:
            parsed[_normalize_label_key(raw_label)] = normalized_level

    return parsed


def normalize_risk_label(raw_label: str, label_map: Optional[str] = None) -> Optional[str]:
    label_key = _normalize_label_key(raw_label)
    configured_map = _parse_label_map(label_map or settings.KOELECTRA_LABEL_MAP)
    return configured_map.get(label_key) or _CANONICAL_LABELS.get(label_key)


def _extract_first_prediction(raw_prediction: Any) -> Optional[Dict[str, Any]]:
    if isinstance(raw_prediction, dict):
        return raw_prediction

    if not isinstance(raw_prediction, list) or not raw_prediction:
        return None

    first = raw_prediction[0]
    if isinstance(first, dict):
        return first
    if isinstance(first, list) and first and isinstance(first[0], dict):
        return first[0]
    return None


def prediction_to_risk_result(
    prediction: Dict[str, Any],
    *,
    label_map: Optional[str] = None,
    min_confidence: float = 0.0,
) -> Optional[Dict[str, Any]]:
    raw_label = str(prediction.get("label", ""))
    risk_level = normalize_risk_label(raw_label, label_map)
    if risk_level is None:
        return None

    try:
        confidence = float(prediction.get("score", 0.0))
    except (TypeError, ValueError):
        return None

    if confidence < min_confidence:
        return None

    risk_types = [] if risk_level == "LOW" else ["KoELECTRA 위험도 분류"]
    matched_rules = [
        f"KoELECTRA 모델 예측: {risk_level} (confidence {confidence:.2f})"
    ]

    return {
        "risk_level": risk_level,
        "risk_score": _RISK_SCORE_BY_LEVEL[risk_level],
        "risk_types": risk_types,
        "matched_rules": matched_rules,
    }


class KoElectraRiskClassifier:
    def __init__(self) -> None:
        model_name = settings.KOELECTRA_MODEL_NAME_OR_PATH.strip()
        if not model_name:
            raise ValueError("KOELECTRA_MODEL_NAME_OR_PATH is empty")

        from transformers import (  # noqa: PLC0415
            AutoModelForSequenceClassification,
            AutoTokenizer,
            pipeline,
        )

        local_files_only = not settings.ALLOW_MODEL_DOWNLOAD
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            local_files_only=local_files_only,
        )
        model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            local_files_only=local_files_only,
        )
        self._pipeline = pipeline(
            "text-classification",
            model=model,
            tokenizer=tokenizer,
            device=settings.KOELECTRA_DEVICE,
        )

    def predict(self, clause_text: str) -> Optional[Dict[str, Any]]:
        raw_prediction = self._pipeline(
            clause_text,
            truncation=True,
            max_length=settings.KOELECTRA_MAX_LENGTH,
        )
        prediction = _extract_first_prediction(raw_prediction)
        if prediction is None:
            return None

        return prediction_to_risk_result(
            prediction,
            min_confidence=settings.KOELECTRA_MIN_CONFIDENCE,
        )


@lru_cache(maxsize=1)
def _get_classifier() -> Optional[KoElectraRiskClassifier]:
    if not settings.USE_KOELECTRA_CLASSIFIER:
        return None

    try:
        return KoElectraRiskClassifier()
    except Exception as exc:
        logger.warning("KoELECTRA classifier is disabled: %s", exc)
        return None


def classify_with_koelectra(clause_text: str) -> Optional[Dict[str, Any]]:
    classifier = _get_classifier()
    if classifier is None:
        return None
    return classifier.predict(clause_text)
