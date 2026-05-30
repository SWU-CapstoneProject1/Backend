import unittest

from app.services import analyze_pipeline
from app.services.koelectra_classifier import (
    normalize_risk_label,
    prediction_to_risk_result,
)


class KoElectraClassifierTests(unittest.TestCase):
    def test_normalize_risk_label_uses_default_and_custom_label_maps(self):
        self.assertEqual(normalize_risk_label("LABEL_2"), "HIGH")
        self.assertEqual(
            normalize_risk_label("bad_clause", "ok:LOW,warn:MEDIUM,bad_clause:HIGH"),
            "HIGH",
        )

    def test_prediction_to_risk_result_maps_prediction_to_pipeline_shape(self):
        result = prediction_to_risk_result(
            {"label": "LABEL_1", "score": 0.82},
            min_confidence=0.5,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["risk_level"], "MEDIUM")
        self.assertEqual(result["risk_score"], 2)
        self.assertEqual(result["risk_types"], ["KoELECTRA 위험도 분류"])

    def test_prediction_to_risk_result_returns_none_below_confidence(self):
        result = prediction_to_risk_result(
            {"label": "LABEL_2", "score": 0.2},
            min_confidence=0.5,
        )

        self.assertIsNone(result)

    def test_analyze_pipeline_uses_koelectra_when_available(self):
        original = analyze_pipeline.classify_with_koelectra
        try:
            analyze_pipeline.classify_with_koelectra = lambda _: {
                "risk_level": "HIGH",
                "risk_score": 5,
                "risk_types": ["KoELECTRA 위험도 분류"],
                "matched_rules": ["model"],
            }

            result = analyze_pipeline.classify_clause_risk("일반 문장")
        finally:
            analyze_pipeline.classify_with_koelectra = original

        self.assertEqual(result["risk_level"], "HIGH")
        self.assertEqual(result["matched_rules"], ["model"])


if __name__ == "__main__":
    unittest.main()
