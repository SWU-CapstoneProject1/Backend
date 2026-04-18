# YakganDongui

AI 기반 불공정 약관 탐지 플랫폼

---

## Overview

YakganDongui는 이용약관 텍스트를 분석하여 불공정 가능성이 있는 조항을 탐지하고,  
공정거래위원회 심결례를 기반으로 근거 중심의 분석 결과를 제공하는 시스템이다.

일반 사용자가 이해하기 어려운 약관 구조를 조항 단위로 분해하고,  
위험도를 분류한 뒤 유사 사례를 연결하여 판단을 보조하는 것을 목표로 한다.

---

## Features

- 약관 텍스트 입력 기반 분석
- 조항 단위 분리 및 전처리
- 규칙 기반 위험도 분류 (HIGH / MEDIUM / LOW)
- RAG 기반 공정위 심결례 검색
- 조항별 설명 생성
- FastAPI 기반 REST API 제공

---

## System Architecture

```
Input (Text / File / URL)
        ↓
Text Extraction (OCR / PDF / Crawling)
        ↓
Clause Splitter
        ↓
Risk Classification (Rule-based → Model 확장 예정)
        ↓
RAG Retriever (SentenceTransformer + FAISS)
        ↓
LLM Explanation (Claude API)
        ↓
API Response
```

---

## Tech Stack

### Backend
- FastAPI
- SQLAlchemy

### AI / NLP
- Sentence Transformers
- FAISS
- Claude API (Anthropic)

### Data Processing
- PyMuPDF
- PaddleOCR
- Playwright

---

## Project Structure

```
Backend/
├── app/
│   ├── api/routes/
│   │   └── analyze.py
│   ├── services/
│   │   ├── analyze_pipeline.py
│   │   ├── clause_splitter.py
│   │   ├── precedent_retriever.py
│   │   └── llm_explainer.py
│   ├── schemas/
│   ├── core/
│   └── main.py
│
├── data_collection/
│   ├── collect_ftc_cases.py
│   ├── preprocess_ftc_for_rag.py
│   ├── build_faiss_index.py
│   └── search_ftc_rag.py
```

---

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

### Run

```bash
python -m uvicorn app.main:app --reload
```

Swagger UI:

```
http://127.0.0.1:8000/docs
```

---

## API

### Analyze Terms (Immediate)

```
POST /api/analyze
```

**Request:**

```json
{
  "text": "약관 전체 텍스트"
}
```

**Response:**

```json
{
  "summary": {
    "total_clauses": 5,
    "high_risk": 2,
    "medium_risk": 1,
    "low_risk": 2
  },
  "clauses": []
}
```

---

## Current Status

| 항목 | 상태 |
|------|------|
| Data collection | ✅ 완료 |
| RAG retrieval | ✅ 구현 완료 |
| Analysis pipeline | ✅ MVP 구현 완료 |
| API server | ✅ 구현 완료 |
| Frontend | ⏳ 미구현 |
| Model-based classification | 🔜 예정 |

---

## Roadmap

- [ ] KoELECTRA 기반 위험도 분류 모델 적용
- [ ] 약관 도메인 데이터셋 구축
- [ ] RAG 검색 품질 개선
- [ ] 프론트엔드 UI 개발
- [ ] 분석 리포트 기능 추가

---

## Notes

- 본 프로젝트는 학술 및 연구 목적으로 개발됨
- 일부 기능은 MVP 수준으로 구현되어 있으며 지속적으로 개선 예정
