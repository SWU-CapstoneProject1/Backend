import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.analysis import AnalysisResult
from app.services.stats_service import get_stats


class StatsServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_get_stats_returns_zero_when_no_analysis_results_exist(self):
        stats = get_stats(self.db)

        self.assertEqual(stats.total_analyses, 0)
        self.assertEqual(stats.total_danger, 0)
        self.assertEqual(stats.total_services, 0)

    def test_get_stats_aggregates_saved_analysis_results(self):
        self.db.add_all(
            [
                AnalysisResult(
                    id="job-1",
                    service_name="service-a",
                    total_clauses=3,
                    high_risk=2,
                    medium_risk=1,
                    low_risk=0,
                    overall_risk_ratio=0.7,
                    result_json="{}",
                ),
                AnalysisResult(
                    id="job-2",
                    service_name="service-a",
                    total_clauses=2,
                    high_risk=0,
                    medium_risk=1,
                    low_risk=1,
                    overall_risk_ratio=0.2,
                    result_json="{}",
                ),
                AnalysisResult(
                    id="job-3",
                    service_name="",
                    total_clauses=1,
                    high_risk=1,
                    medium_risk=0,
                    low_risk=0,
                    overall_risk_ratio=1.0,
                    result_json="{}",
                ),
            ]
        )
        self.db.commit()

        stats = get_stats(self.db)

        self.assertEqual(stats.total_analyses, 3)
        self.assertEqual(stats.total_danger, 3)
        self.assertEqual(stats.total_services, 1)


if __name__ == "__main__":
    unittest.main()
