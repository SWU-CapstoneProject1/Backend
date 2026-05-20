# Codex 작업 인수인계 문서

작성일: 2026-05-20
프로젝트 경로: `C:\Users\sally\OneDrive\문서\GitHub\SWU-CapstoneProject1\Backend`
현재 브랜치: `main`

이 문서는 Codex 세션이 종료되어도 다음 작업자가 현재 프로젝트 상태를 바로 파악할 수 있도록 작성한 백엔드 작업 기록이다.
프론트엔드 연동은 내일 진행 예정이며, 이 문서는 현재까지 백엔드와 문서 중심으로 진행한 내용을 정리한다.

## 1. 프로젝트 개요

프로젝트명은 **약관동의(YakganDongui)** 이다.

목표는 사용자가 직접 읽기 어려운 약관을 입력하면 백엔드가 약관 텍스트를 추출하고, 조항 단위로 나눈 뒤 위험도를 분석하여 사용자가 이해하기 쉬운 설명과 관련 공정위 심결례를 제공하는 것이다.

현재 백엔드는 FastAPI 기반으로 구성되어 있고, 주요 흐름은 다음과 같다.

1. 사용자가 텍스트, URL, PDF, 이미지 중 하나로 약관을 입력한다.
2. 백엔드가 입력 방식에 따라 텍스트를 추출한다.
3. 약관을 조항 단위로 분리한다.
4. 규칙 기반으로 위험도를 `HIGH`, `MEDIUM`, `LOW`로 분류한다.
5. FAISS/RAG 기반으로 관련 공정위 심결례를 검색한다.
6. LLM 설명 또는 fallback 설명을 생성한다.
7. 결과를 DB에 저장하고 API 응답으로 제공한다.
8. 필요하면 분석 결과 PDF 리포트를 생성한다.

## 2. 주요 백엔드 API

현재 핵심 API는 다음과 같다.

- `POST /api/analyze/text`
  - 텍스트 직접 입력 분석 시작
  - `job_id`를 즉시 반환하고 분석은 `BackgroundTasks`에서 수행

- `POST /api/analyze/url`
  - URL 입력 분석 시작
  - URL에서 약관 본문을 추출한 뒤 분석

- `POST /api/analyze/file`
  - PDF 또는 이미지 파일 업로드 분석 시작
  - PDF, PNG, JPG, WEBP, BMP, TIFF 지원

- `POST /api/analyze`
  - 즉시 분석용 기존 API
  - 분석 완료 결과를 바로 반환

- `GET /api/result/{job_id}`
  - 분석 결과 조회
  - 프론트는 비동기 분석 요청 후 이 API로 polling하면 된다.

- `GET /api/report/{job_id}/pdf`
  - 분석 결과 PDF 리포트 다운로드

## 3. 최신 main 반영 내역

작업 시작 전 최신 `main`을 pull했다.

```powershell
git pull --ff-only origin main
```

결과는 최신 상태였다.

이전에 팀원 `jeongjihyunn`님의 PR이 `main`에 merge되어 있었고, 그 내용은 다음과 같았다.

- Dockerfile 추가
- Tesseract OCR 및 한국어 OCR 데이터 설치 설정 추가
- `BackgroundTasks` 기반 비동기 분석 처리 추가
- 분석 요청 시 `job_id` 즉시 반환
- `/api/result/{job_id}` polling 구조 확인
- PDF 리포트 다운로드 확인
- `.claude` gitignore 추가
- requirements 통합

해당 변경 이후 현재 백엔드는 텍스트, URL, 파일 분석 요청에서 `job_id`를 먼저 반환하고 백그라운드에서 분석을 진행하는 구조다.

## 4. 지금까지 진행한 작업

### 4.1 가상환경 확인

초기에 가상환경 존재 여부와 Python 버전을 확인했다.

```powershell
.\.venv\Scripts\python.exe --version
```

확인 결과:

```text
Python 3.13.7
```

PowerShell에서 직접 활성화하려면 다음 명령을 사용하면 된다.

```powershell
.\.venv\Scripts\Activate.ps1
```

Codex 작업에서는 activation이 세션 간 유지되지 않으므로, 대부분 `.venv\Scripts\python.exe`를 직접 호출했다.

### 4.2 발표 스크립트 기반 프로젝트 상태 분석

검토한 파일:

- `docs/약관동의_중간발표_스크립트.md`
- `app/api/routes/analyze.py`
- `app/services/analyze_pipeline.py`
- `app/services/file_extractor.py`
- `app/services/precedent_retriever.py`
- `app/services/result_service.py`
- `app/api/routes/report.py`
- `app/main.py`
- `data_collection/*`

초기 스크립트에는 다음 항목이 미구현 또는 진행 중으로 적혀 있었다.

- 이미지 OCR 미구현
- 분석 시작 CTA 비동기 처리 진행 중
- 심결례 유사도 임계값 필터링 미구현
- 리포트 기능 예정

하지만 최신 `main` 반영 후 확인한 실제 백엔드 상태는 다음과 같았다.

- 이미지 OCR은 이미 구현되어 있었다.
- FastAPI `BackgroundTasks` 기반 비동기 분석 시작도 구현되어 있었다.
- PDF 리포트 생성 API도 구현되어 있었다.
- 심결례 유사도 임계값 필터링은 없어서 새로 구현했다.
- 스캔 PDF OCR fallback은 부족해서 새로 보강했다.

### 4.3 RAG 전처리 스크립트 SyntaxError 수정

문제가 있던 파일:

- `data_collection/preprocess_ftc_for_rag.py`

기존 문제:

```python
r"이하\s+[\""\"]?\w+[\""\"]?\s*(?:이|라)\s*한다"
```

따옴표 escaping이 깨져 `SyntaxError`가 발생했다.

수정 후:

```python
r'이하\s+["“”]?\w+["“”]?\s*(?:이|라)\s*한다'
```

수정 후 다음 명령으로 검증했다.

```powershell
.\.venv\Scripts\python.exe data_collection\preprocess_ftc_for_rag.py
```

결과:

```text
전처리 완료
- 입력 문서 수: 20
- 변환 성공 수: 20
- 스킵 수: 0
```

### 4.4 FAISS 인덱스 재생성 검증

RAG 전처리 후 FAISS 인덱스 재생성도 확인했다.

```powershell
.\.venv\Scripts\python.exe data_collection\build_faiss_index.py
```

처음에는 HuggingFace 모델 접근이 sandbox 네트워크 제한으로 실패했다. 승인 후 다시 실행해서 성공했다.

결과:

```text
문서 수: 20
모델 로드: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
임베딩 shape: (20, 384)
인덱스 생성 완료
- index: data_collection\data\index\ftc_faiss.index
- metadata: data_collection\data\index\ftc_faiss_metadata.json
- config: data_collection\data\index\ftc_faiss_config.json
```

주의:

- `data_collection/data/`는 `.gitignore` 대상이다.
- 따라서 재생성된 인덱스 파일은 로컬에는 있지만 Git commit 대상은 아니다.

### 4.5 심결례 유사도 임계값 필터링 구현

수정한 파일:

- `app/core/config.py`
- `app/services/analyze_pipeline.py`

추가한 설정:

```python
PRECEDENT_MIN_SIMILARITY: float = 0.2
```

추가한 함수:

```python
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
```

적용 위치:

```python
reranked = filter_cases_by_similarity(rerank_cases(text, retrieved))
```

현재 기본 threshold는 `0.2`다. 실제 데이터 품질에 따라 `0.25`, `0.3` 등으로 조정 가능하다.

샘플 점검 결과:

- 약관 일방 변경 문장
- 환불 제한 문장
- 손해 책임 면책 문장

위 3개 샘플에서 검색 결과가 threshold 통과 후에도 유지되는 것을 확인했다.

### 4.6 스캔 PDF OCR fallback 구현

수정한 파일:

- `app/core/config.py`
- `app/services/file_extractor.py`
- `docs/OCR_SETUP.md`

추가한 설정:

```python
OCR_PDF_MAX_PAGES: int = 20
OCR_PDF_DPI: int = 200
```

기존 PDF 처리:

- PyMuPDF로 텍스트 PDF에서 텍스트를 추출
- 이미지 기반 PDF는 텍스트 추출 실패

개선 후 PDF 처리:

1. 먼저 PyMuPDF로 텍스트 추출을 시도한다.
2. 추출된 텍스트가 충분하면 그대로 반환한다.
3. 텍스트가 없거나 너무 짧으면 PDF 페이지를 이미지로 렌더링한다.
4. 렌더링된 이미지를 Tesseract OCR에 넘긴다.
5. OCR 결과가 충분히 usable하면 반환한다.

핵심 함수:

- `_extract_text_from_pdf_pages`
- `_extract_text_from_scanned_pdf`
- `_is_ocr_text_usable`

`_is_ocr_text_usable`은 OCR 결과가 길이만 충분하고 실제 한글/영문 글자가 거의 없는 숫자/기호 노이즈일 때 분석으로 넘기지 않도록 막는다.

### 4.7 OCR 실제 검증

확인한 Tesseract 상태:

```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --list-langs
```

초기에는 전역 tessdata에 다음만 있었다.

```text
eng
osd
```

프로젝트 로컬에는 다음 파일이 있었다.

```text
ocr\tessdata\eng.traineddata
ocr\tessdata\kor.traineddata
ocr\tessdata\osd.traineddata
```

한국어 OCR 실행 중 보조 언어 데이터가 필요해서 공식 저장소에서 다음 파일을 추가로 받았다.

```text
ocr\tessdata\chi_tra.traineddata
```

이후 로컬 tessdata 언어 목록:

```text
chi_tra
eng
kor
osd
```

검증 결과:

- 영어 이미지 OCR은 정상 추출된다.
- 현재 로컬 한국어 OCR은 숫자 위주로 깨지는 품질 문제가 있다.
- 이 문제 때문에 숫자형 깨짐 결과는 분석 파이프라인으로 넘기지 않도록 차단 로직을 추가했다.

영어 OCR 샘플 결과:

```text
Terms OCR Test
The company is not responsible for damages.
Refunds may be restricted.
```

한국어 OCR 샘플 결과는 숫자/기호 위주로 깨졌고, 최종적으로 다음 오류를 반환하도록 처리했다.

```text
이미지에서 분석 가능한 약관 텍스트를 충분히 추출하지 못했습니다.
```

즉, 현재 상태는 “OCR 파이프라인은 동작하지만, 로컬 Tesseract 한국어 인식 품질은 추가 개선 필요”다.

### 4.8 OCR 문서 업데이트

수정한 파일:

- `docs/OCR_SETUP.md`

추가한 내용:

- `OCR_PDF_MAX_PAGES`
- `OCR_PDF_DPI`
- 스캔 PDF OCR fallback 설명
- OCR 결과가 너무 짧거나 숫자/기호 노이즈면 거절한다는 설명
- 한국어 OCR이 깨질 때 `kor.traineddata`, `chi_tra.traineddata` 확인 필요

### 4.9 발표 스크립트 최신화

수정한 파일:

- `docs/약관동의_중간발표_스크립트.md`

반영한 내용:

- 백엔드 P1 기능 대부분 구현 완료로 표현 수정
- PDF 업로드 설명에 스캔 PDF OCR fallback 추가
- 분석 시작 처리에서 `job_id` 즉시 반환 및 백그라운드 분석 구조 설명 추가
- 이미지 OCR 구현 완료로 수정
- 심결례 유사도 임계값 필터링 구현 완료로 수정
- PDF 리포트 백엔드 API 구현 완료 및 프론트 다운로드 버튼 연동 예정으로 수정
- API 설명을 `POST /api/analyze/text`, `/url`, `/file`, `GET /api/result/{job_id}` 구조로 수정
- 마무리 문장에서 앞으로 할 일을 프론트 상세 UI, 결과 시각화, 리포트 다운로드 버튼 연동, OCR 품질 검증 중심으로 정리

### 4.10 테스트 정리 및 추가

기존 `test_analyze_pipeline.py`는 import 시 바로 실행되는 구조였다. 이를 `main()` 가드로 감싸서 테스트 discovery 때 의도치 않게 분석이 실행되지 않도록 수정했다.

추가한 테스트 파일:

- `tests/test_api_endpoints.py`
- `tests/test_file_extractor_ocr.py`
- `tests/test_preprocess_and_rag.py`

테스트 범위:

- `/api/analyze/text`가 `job_id` 즉시 반환하는지
- `/api/analyze/url`이 `job_id` 즉시 반환하는지
- `/api/analyze/file`이 PDF 파일을 받고 `job_id`를 반환하는지
- `/api/result/{job_id}` 결과 조회가 가능한지
- `/api/report/{job_id}/pdf` PDF 다운로드 응답이 가능한지
- RAG 전처리 boilerplate 제거와 중복 문장 제거
- RAG threshold 필터링
- 스캔 PDF OCR fallback 호출
- 너무 짧은 OCR 결과 reject
- 숫자형 OCR 노이즈 결과 reject

최종 테스트 결과:

```powershell
.\.venv\Scripts\python.exe -m unittest discover tests -v
```

```text
Ran 10 tests
OK
```

문법 검사:

```powershell
.\.venv\Scripts\python.exe -m compileall app data_collection tests
```

결과:

```text
통과
```

diff 검사:

```powershell
git diff --check
```

결과:

```text
문제 없음
```

## 5. 현재 변경된 주요 파일

현재 로컬에서 수정된 주요 파일은 다음과 같다.

- `app/core/config.py`
  - OCR PDF 설정 추가
  - RAG 유사도 threshold 설정 추가

- `app/services/analyze_pipeline.py`
  - `filter_cases_by_similarity` 추가
  - rerank 이후 threshold 필터링 적용

- `app/services/file_extractor.py`
  - 스캔 PDF OCR fallback 추가
  - OCR 결과 usable 검증 추가
  - tessdata 경로 처리 보완

- `data_collection/preprocess_ftc_for_rag.py`
  - `_BOILERPLATE` 정규식 SyntaxError 수정

- `docs/OCR_SETUP.md`
  - 스캔 PDF OCR fallback 및 OCR 품질 검증 기준 문서화

- `docs/약관동의_중간발표_스크립트.md`
  - 최신 구현 상태 반영

- `test_analyze_pipeline.py`
  - import 시 즉시 실행되지 않도록 `main()` 가드 추가

- `tests/test_api_endpoints.py`
  - API endpoint 테스트 추가

- `tests/test_file_extractor_ocr.py`
  - OCR fallback 및 reject 테스트 추가

- `tests/test_preprocess_and_rag.py`
  - 전처리 및 RAG threshold 테스트 추가

## 6. 현재 Git 상태에서 주의할 점

현재 `git status` 기준으로 로컬 변경사항이 남아 있다.

대표 상태:

```text
M app/core/config.py
M app/services/analyze_pipeline.py
M app/services/file_extractor.py
M data_collection/preprocess_ftc_for_rag.py
M docs/OCR_SETUP.md
M test_analyze_pipeline.py
?? docs/약관동의_중간발표_스크립트.md
?? tests/
```

주의:

- `docs/약관동의_중간발표_스크립트.md`는 처음부터 untracked 상태였다.
- 이 문서는 발표 스크립트로 계속 관리하려면 commit에 포함해야 한다.
- `tests/`도 새로 추가한 테스트 디렉터리라 commit에 포함해야 한다.
- Git 경고로 `C:\Users\sally\.config\git\ignore` 접근 권한 경고가 계속 보인다. pull/test에는 치명적이지 않았지만, 필요하면 Windows 권한을 정리하면 된다.

## 7. 프론트 연동 관련 확인

프론트 작업은 내일 진행하기로 했다.

현재 `SWU-CapstoneProject1` 하위에서는 프론트 프로젝트로 보이는 `package.json`이나 `src`가 발견되지 않았다. 넓게 검색했을 때 관련 없어 보이는 `BACKEND/react-crud/package.json`만 확인되었다.

따라서 실제 프론트 연동을 진행하려면 다음 중 하나가 필요하다.

- 프론트엔드 레포 경로 제공
- 프론트엔드 코드를 현재 workspace에 clone
- 프론트엔드가 별도 브랜치/폴더에 있다면 정확한 위치 전달

프론트에서 연동해야 하는 백엔드 API는 다음과 같다.

- 분석 요청:
  - `POST /api/analyze/text`
  - `POST /api/analyze/url`
  - `POST /api/analyze/file`

- 결과 polling:
  - `GET /api/result/{job_id}`

- PDF 리포트 다운로드:
  - `GET /api/report/{job_id}/pdf`

프론트에서 구현할 UI:

- 분석 요청 후 `job_id` 저장
- 결과 완료 전 loading/polling 상태 표시
- 조항별 드롭다운
- hover 시 AI 요약 표시
- 위험도 게이지 차트
- HIGH/MEDIUM/LOW 색상 하이라이트
- PDF 리포트 다운로드 버튼

## 8. 앞으로 해야 할 일

### 8.1 바로 해야 할 일

1. 현재 로컬 변경사항 commit 여부 결정
   - 권장 commit 메시지:
     ```text
     Fix RAG preprocessing and improve OCR validation
     ```

2. 프론트 프로젝트 경로 확인
   - 프론트 코드 위치가 확인되면 API 연동 작업 진행

3. 실제 한국어 약관 이미지와 스캔 PDF 샘플로 OCR 품질 재검증
   - 현재 합성 한글 이미지에서는 Tesseract 결과가 숫자 위주로 깨졌다.
   - 실제 스크린샷/스캔본에서는 결과가 다를 수 있으므로 별도 검증 필요

### 8.2 OCR 품질 개선 후보

현재 Tesseract 한국어 OCR 품질이 낮게 나왔다. 개선 후보는 다음과 같다.

1. 실제 약관 이미지 샘플 확보 후 Tesseract 옵션 튜닝
   - `OCR_PSM`
   - 이미지 확대 배율
   - thresholding
   - grayscale/autocontrast 외 전처리

2. OCR 언어 데이터 교체
   - `tessdata`
   - `tessdata_best`
   - `tessdata_fast`

3. PaddleOCR 또는 EasyOCR 비교 검토
   - 한국어 약관 OCR 품질은 Tesseract보다 PaddleOCR이 나을 가능성이 있다.
   - 단, Docker 이미지 크기와 설치 복잡도가 증가할 수 있다.

### 8.3 RAG 품질 개선 후보

현재 RAG 데이터는 20개 문서 기준으로 인덱스가 생성되어 있다. MVP 검증은 가능하지만 추천 품질을 높이려면 다음이 필요하다.

1. 공정위 심결례 데이터 추가 수집
2. `PRECEDENT_MIN_SIMILARITY` 값 튜닝
3. semantic RAG 사용 여부 결정
   - 현재 `precedent_retriever.py`는 환경변수 `USE_SEMANTIC_RAG`가 true일 때 SentenceTransformer 검색을 사용한다.
   - false면 keyword search fallback을 사용한다.
4. 검색 결과 title/preview/tags 품질 점검
5. 약관 위험 유형별 query 확장 또는 rerank 로직 개선

### 8.4 테스트 추가 후보

현재 10개 테스트가 통과한다. 추가로 넣으면 좋은 테스트는 다음과 같다.

1. 실제 DB를 임시 SQLite로 띄운 end-to-end 분석 테스트
2. `BackgroundTasks` 실행 후 job status가 `done`으로 바뀌는 테스트
3. URL 접근 실패, 404, timeout 테스트
4. PDF 텍스트 추출 성공 테스트
5. 스캔 PDF OCR 실패 시 job status가 `failed`로 저장되는 테스트
6. 리포트 PDF가 실제로 열리는지 검증하는 테스트

### 8.5 문서 정리 후보

1. README 최신화
   - 현재 README에는 오래된 내용과 일부 인코딩 문제가 섞여 있었던 흔적이 있다.
   - 실제 API 구조와 Docker/OCR 설정을 반영하면 좋다.

2. 발표 스크립트 최종 검토
   - 백엔드 구현 완료 항목과 프론트 예정 항목을 명확히 구분해야 한다.

3. `.env.example` 추가
   - OCR/RAG/LLM 설정값을 팀원이 쉽게 맞출 수 있도록 예시 파일을 만들면 좋다.

예시:

```env
DATABASE_URL=sqlite:///./yakgandongui.db
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
TESSDATA_DIR=ocr/tessdata
OCR_LANGUAGE=kor+eng
OCR_PSM=6
OCR_MIN_TEXT_LENGTH=20
OCR_PDF_MAX_PAGES=20
OCR_PDF_DPI=200
PRECEDENT_MIN_SIMILARITY=0.2
USE_SEMANTIC_RAG=false
ALLOW_MODEL_DOWNLOAD=false
ANTHROPIC_API_KEY=
LAW_API_KEY=
```

## 9. 다음 Codex가 가장 먼저 보면 좋은 파일

다음 작업자가 프로젝트를 이어받을 때 우선순위로 보면 좋은 파일은 다음과 같다.

1. `docs/CODEX_작업_인수인계.md`
2. `app/api/routes/analyze.py`
3. `app/services/analyze_pipeline.py`
4. `app/services/file_extractor.py`
5. `app/services/precedent_retriever.py`
6. `app/services/result_service.py`
7. `app/api/routes/report.py`
8. `docs/OCR_SETUP.md`
9. `docs/약관동의_중간발표_스크립트.md`
10. `tests/`

## 10. 최종 상태 요약

현재 백엔드는 다음 수준까지 정리되어 있다.

- 텍스트 분석 가능
- URL 분석 가능
- PDF 분석 가능
- 이미지 OCR 분석 가능
- 스캔 PDF OCR fallback 구현됨
- 비동기 분석 시작 가능
- `job_id` 기반 결과 조회 가능
- 위험도 0~100점 계산 가능
- 공정위 심결례 RAG 검색 가능
- RAG 유사도 threshold 필터링 가능
- PDF 리포트 생성 가능
- 에러 응답 구조 통일됨
- 테스트 10개 통과

남은 핵심은 프론트 연동과 실제 한국어 OCR 품질 개선이다.
