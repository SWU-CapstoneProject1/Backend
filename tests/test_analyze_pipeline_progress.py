import unittest
from unittest.mock import patch

from app.services.analyze_pipeline import analyze_terms_text


class AnalyzePipelineProgressTests(unittest.TestCase):
    def test_analyze_terms_text_reports_clause_progress(self):
        events = []
        clauses = [
            {"clause_id": 1, "title": "제1조", "content": "첫 번째 테스트 조항입니다."},
            {"clause_id": 2, "title": "제2조", "content": "두 번째 테스트 조항입니다."},
        ]
        risk = {
            "risk_level": "LOW",
            "risk_score": 0,
            "risk_types": [],
            "matched_rules": [],
        }
        explanation = {
            "summary": "요약",
            "plain_explanation": "쉬운 설명",
            "legal_rationale": "",
            "consumer_warning": "",
            "confidence_note": "",
        }

        with (
            patch("app.services.analyze_pipeline._get_retriever") as get_retriever,
            patch("app.services.analyze_pipeline.split_clauses", return_value=clauses),
            patch("app.services.analyze_pipeline.classify_clause_risk", return_value=risk),
            patch("app.services.analyze_pipeline.generate_llm_explanation", return_value=explanation),
        ):
            get_retriever.return_value.search.return_value = []

            analyze_terms_text("terms", progress_callback=lambda **payload: events.append(payload))

        stages = [event["stage"] for event in events]
        percents = [event["progress_percent"] for event in events if "progress_percent" in event]

        self.assertIn("splitting", stages)
        self.assertIn("generating_explanation", stages)
        self.assertIn("summarizing", stages)
        self.assertEqual(events[-1]["stage"], "summarizing")
        self.assertEqual(events[-1]["progress_percent"], 92)
        self.assertTrue(all(left <= right for left, right in zip(percents, percents[1:])))
        self.assertTrue(any(event.get("current_clause") == 2 for event in events))


if __name__ == "__main__":
    unittest.main()
