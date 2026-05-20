import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from app.schemas.schemas import JobStatus, ResultResponse


def _override_db():
    yield object()


class ApiEndpointTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_db] = _override_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_analyze_text_returns_job_id_immediately(self):
        job_id = str(uuid.uuid4())
        job = SimpleNamespace(id=job_id, status="pending")

        with (
            patch("app.api.routes.analyze.create_analysis_job", return_value=job),
            patch("app.api.routes.analyze._bg_text_analysis") as background_task,
        ):
            response = self.client.post(
                "/api/analyze/text",
                json={"text": "제1조 약관 테스트 문장입니다. 충분한 길이의 텍스트입니다.", "session_key": "s"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job_id"], job_id)
        background_task.assert_called_once()

    def test_analyze_url_returns_job_id_immediately(self):
        job_id = str(uuid.uuid4())
        job = SimpleNamespace(id=job_id, status="pending")

        with (
            patch("app.api.routes.analyze.create_analysis_job", return_value=job),
            patch("app.api.routes.analyze._bg_url_analysis") as background_task,
        ):
            response = self.client.post(
                "/api/analyze/url",
                json={"url": "https://example.com/terms", "session_key": "s"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job_id"], job_id)
        background_task.assert_called_once()

    def test_analyze_file_accepts_pdf_and_returns_job_id(self):
        job_id = str(uuid.uuid4())
        job = SimpleNamespace(id=job_id, status="pending")

        with (
            patch("app.api.routes.analyze.create_analysis_job", return_value=job),
            patch("app.api.routes.analyze._bg_file_analysis") as background_task,
        ):
            response = self.client.post(
                "/api/analyze/file",
                data={"session_key": "s", "service_name": "svc"},
                files={"file": ("terms.pdf", b"%PDF-1.4\n", "application/pdf")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job_id"], job_id)
        background_task.assert_called_once()

    def test_result_endpoint_returns_saved_result(self):
        job_id = str(uuid.uuid4())
        result = ResultResponse(
            job_id=job_id,
            status=JobStatus.done,
            service_name="svc",
            risk_score=20.0,
            danger_count=0,
            caution_count=1,
            safe_count=1,
            clauses=[],
            precedents=[],
        )

        with patch("app.api.routes.result.get_result", return_value=result):
            response = self.client.get(f"/api/result/{job_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job_id"], job_id)

    def test_report_endpoint_downloads_pdf(self):
        job_id = str(uuid.uuid4())
        result = ResultResponse(
            job_id=job_id,
            status=JobStatus.done,
            service_name="svc",
            risk_score=20.0,
            danger_count=0,
            caution_count=1,
            safe_count=1,
            clauses=[],
            precedents=[],
        )

        with (
            patch("app.api.routes.report.get_result", return_value=result),
            patch("app.api.routes.report.generate_pdf_report", return_value=b"%PDF-1.4"),
        ):
            response = self.client.get(f"/api/report/{job_id}/pdf")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"%PDF-1.4")
        self.assertEqual(response.headers["content-type"], "application/pdf")


if __name__ == "__main__":
    unittest.main()
