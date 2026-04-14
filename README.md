# 약간동의 (YakganDongui)

> **"전체 동의"를 누르기 전에, 약관을 약간이라도 알고 동의하세요.**

AI 기반 불공정 약관 탐지 플랫폼 — 이용약관을 입력하면 불공정 조항을 자동으로 탐지하고, 공정거래위원회 심결례와 연결하여 근거 기반 분석 리포트를 제공합니다.

---

## 프로젝트 소개

이용약관은 대부분 길고 법률 용어가 많아 일반 사용자가 직접 읽고 위험성을 판단하기 어렵습니다. 소비자에게 불리한 조항이 포함되어 있어도 이를 인식하지 못한 채 동의하는 경우가 많습니다.

**약간동의**는 이 문제를 AI로 해결합니다.

약관 텍스트를 입력하면 조항 단위로 분리하여 위험도를 분류하고, 유사한 공정위 심결례를 추천하며, 쉬운 언어로 설명을 제공합니다. 단순 요약이 아니라 **근거 기반 분석**이 핵심입니다.

> 공정거래위원회도 "AI 융합 약관심사 플랫폼" 구축을 추진하고 있어, 본 프로젝트는 실제 정책 흐름과 맞닿아 있습니다.

---

## 주요 기능

### 1. 약관 입력
- **텍스트 붙여넣기** — 약관 원문 직접 입력
- **PDF 업로드** — PyMuPDF로 텍스트 추출
- **이미지 업로드** — PaddleOCR로 스캔 약관 처리
- **URL 입력** — Playwright + Trafilatura로 자동 수집

### 2. 분석 리포트
- **위험도 게이지 차트** — 🔴 위험 / 🟡 주의 / 🟢 정상 조항 비율 시각화
- **조항 하이라이트** — 위험 조항 색상 강조 + 클릭 시 상세 설명
- **쉬운 요약** — Claude API가 법률 용어를 일반인 언어로 변환
- **공정위 심결례 추천** — RAG 기반으로 유사 위반 사례 최대 3건 추천
- **PDF 다운로드** — 분석 리포트 PDF 저장

### 3. 보관함
- 분석 기록 저장 및 조회
- 위험도 등급 필터링
- 서비스명 / 날짜 검색

---

## 기술 스택

### Backend
| 분야 | 기술 |
|---|---|
| API 서버 | FastAPI |
| 데이터베이스 | SQLite (개발) / PostgreSQL (배포) |
| 비동기 작업 | Celery + Redis |
| AI 분류 모델 | KoELECTRA (Fine-tuning) |
| LLM 요약 | Claude API (Anthropic) |
| RAG | LangChain + FAISS + Sentence Transformers |

### Frontend
| 분야 | 기술 |
|---|---|
| UI 프레임워크 | React |
| PDF 생성 | html2canvas + jsPDF |

### 데이터 수집
| 분야 | 기술 |
|---|---|
| PDF 추출 | PyMuPDF |
| 이미지 OCR | PaddleOCR |
| 웹 크롤링 | Playwright + Trafilatura |
| 심결례 데이터 | 국가법령정보 Open API (law.go.kr) |

---

## 시스템 아키텍처

```
사용자 입력 (텍스트 / PDF / 이미지 / URL)
        ↓
   텍스트 추출 레이어
   PyMuPDF / PaddleOCR / Playwright
        ↓
   조항 단위 분리 (Regex + SBD)
        ↓
   KoELECTRA 위험도 분류
   🔴 위험 / 🟡 주의 / 🟢 정상
        ↓
   ┌────────────┬─────────────────┐
   │ Claude API │  RAG 심결례 검색 │
   │ 쉬운 요약   │  FAISS + 임베딩 │
   └────────────┴─────────────────┘
        ↓
   분석 리포트 제공
```

---

## 시작하기

### Backend

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에 ANTHROPIC_API_KEY 입력

# DB 초기화
python init_db.py

# 서버 실행
uvicorn app.main:app --reload
```

---

## 팀 소개

서울여자대학교 소프트웨어융합학과 프로젝트종합설계1 약간동의팀

---

## 관련 링크

- [공정거래위원회 AI 융합 약관심사 플랫폼](https://www.ftc.go.kr)
- [ToS;DR](https://tosdr.org) — 해외 유사 서비스
- [CLAUDETTE](https://claudette.eui.eu) — 불공정 약관 자동 탐지 연구

---
