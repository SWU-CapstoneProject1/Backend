import unittest

from app.services.analyze_pipeline import filter_cases_by_similarity
from data_collection import preprocess_ftc_for_rag


class PreprocessAndRagTests(unittest.TestCase):
    def test_clean_summary_removes_boilerplate_and_deduplicates(self):
        raw = (
            '공정거래위원회 의결 제2024-001호 이하 "회사"라 한다. '
            "소비자에게 불리한 약관입니다. 소비자에게 불리한 약관입니다."
        )

        cleaned = preprocess_ftc_for_rag.clean_summary(raw)

        self.assertNotIn("공정거래위원회 의결", cleaned)
        self.assertNotIn("이하", cleaned)
        self.assertEqual(cleaned.count("소비자에게 불리한 약관입니다."), 1)

    def test_filter_cases_by_similarity_uses_score_or_reranked_score(self):
        cases = [
            {"id": "low", "score": 0.1},
            {"id": "base", "score": 0.2},
            {"id": "reranked", "score": 0.05, "reranked_score": 0.35},
            {"id": "invalid", "score": "not-a-number"},
        ]

        filtered = filter_cases_by_similarity(cases, min_similarity=0.2)

        self.assertEqual([case["id"] for case in filtered], ["base", "reranked"])


if __name__ == "__main__":
    unittest.main()
