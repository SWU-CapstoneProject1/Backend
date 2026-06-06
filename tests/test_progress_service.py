import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.analysis import AnalysisResult
from app.models.models import JobStatus
from app.services.analyze_service import create_analysis_job
from app.services.progress_service import get_analysis_progress, update_analysis_progress


class ProgressServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_create_analysis_job_creates_queued_progress(self):
        job = create_analysis_job(self.db, "text", "terms text", service_name="svc", session_key="s")

        progress = get_analysis_progress(self.db, job.id)

        self.assertIsNotNone(progress)
        self.assertEqual(progress.status, JobStatus.pending.value)
        self.assertEqual(progress.progress_percent, 0)
        self.assertEqual(progress.stage, "queued")

    def test_update_analysis_progress_returns_clause_context(self):
        job = create_analysis_job(self.db, "text", "terms text")
        job.status = JobStatus.running
        self.db.commit()

        update_analysis_progress(
            self.db,
            job.id,
            progress_percent=55,
            stage="generating_explanation",
            message="1/2번 조항의 AI 설명을 생성하고 있습니다.",
            current_clause=1,
            total_clauses=2,
            current_clause_title="제1조",
            current_clause_preview="테스트 조항입니다.",
        )

        progress = get_analysis_progress(self.db, job.id)

        self.assertEqual(progress.status, JobStatus.running.value)
        self.assertEqual(progress.progress_percent, 55)
        self.assertEqual(progress.stage, "generating_explanation")
        self.assertEqual(progress.current_clause, 1)
        self.assertEqual(progress.total_clauses, 2)
        self.assertEqual(progress.current_clause_title, "제1조")
        self.assertEqual(progress.current_clause_preview, "테스트 조항입니다.")

    def test_get_analysis_progress_falls_back_to_saved_result(self):
        self.db.add(AnalysisResult(
            id="saved-job",
            service_name="svc",
            total_clauses=1,
            high_risk=0,
            medium_risk=0,
            low_risk=1,
            overall_risk_ratio=0.0,
            result_json="{}",
        ))
        self.db.commit()

        progress = get_analysis_progress(self.db, "saved-job")

        self.assertEqual(progress.status, JobStatus.done.value)
        self.assertEqual(progress.progress_percent, 100)
        self.assertEqual(progress.stage, "completed")


if __name__ == "__main__":
    unittest.main()
