# Codex 작업 인수인계 - KoELECTRA/Gemini 연동

작성일: 2026-05-31
프로젝트 경로: `C:\Users\sally\OneDrive\문서\GitHub\SWU-CapstoneProject1\Backend`
브랜치: `main`
최신 push 커밋: `c563b82 Add KoELECTRA pseudo classifier integration`

## 1. 현재 상태 요약

오늘 작업의 핵심은 다음 세 가지다.

1. 기존 규칙 기반 위험도 분류 위에 KoELECTRA/KR-ELECTRA optional classifier를 연결했다.
2. 규칙 기반 결과를 pseudo-label로 사용해 데모용 KR-ELECTRA checkpoint를 fine-tuning했다.
3. Anthropic Claude 호출부를 Gemini API 호출부로 전환했다.

현재 `main`에는 KoELECTRA 연동 코드, pseudo fine-tuning 스크립트, 테스트, README/env 문서가 push되어 있다.

```text
c563b82 Add KoELECTRA pseudo classifier integration
```

`upload_model.py`는 Hugging Face 업로드에 사용한 1회성 스크립트다. 토큰은 포함하지 않는다.

## 2. KoELECTRA/KR-ELECTRA 연동

선택한 기본 모델은 Hugging Face의 다음 모델이다.

```text
snunlp/KR-ELECTRA-discriminator
```

선정 이유:

- 한국어 ELECTRA 계열 모델
- 사전학습 corpus에 legal text가 포함되어 있어 약관/법률 문체에 비교적 적합
- `AutoModelForSequenceClassification`으로 fine-tuning해 `LOW / MEDIUM / HIGH` 위험도 분류기로 사용할 수 있음

추가된 주요 파일:

```text
app/services/koelectra_classifier.py
scripts/train_koelectra_pseudo.py
tests/test_koelectra_classifier.py
tests/test_koelectra_pseudo_training.py
```

수정된 주요 파일:

```text
app/services/analyze_pipeline.py
app/core/config.py
.env.example
requirements.txt
README.md
```

동작 방식:

1. `classify_clause_risk()`가 먼저 KoELECTRA classifier를 호출한다.
2. 모델이 꺼져 있거나 로드 실패, 낮은 confidence, 라벨 매핑 실패가 발생하면 기존 규칙 기반 분류로 fallback한다.
3. 따라서 모델 연동 문제가 생겨도 기존 분석 API는 계속 동작한다.

## 3. 데모용 pseudo fine-tuning

현재 checkpoint는 사람이 직접 검수한 라벨 데이터로 학습한 모델이 아니다.

기존 규칙 기반 분류 결과를 pseudo-label로 만들어 데모용으로 fine-tuning했다. 발표와 연동 검증용으로는 사용할 수 있지만, 논문/서비스 품질 검증 단계에서는 실제 사람이 라벨링한 약관 조항 데이터로 다시 학습해야 한다.

학습한 라벨:

```text
LOW
MEDIUM
HIGH
```

로컬 학습 결과:

```text
pseudo dataset: 135 rows
LOW: 45
MEDIUM: 45
HIGH: 45
final eval_accuracy: 0.963
```

주의:

- 위 accuracy는 pseudo-label 기준이다.
- 사람이 검수한 정답 라벨 기준 성능이 아니다.
- 실제 서비스/논문 성능 수치로 사용하면 안 된다.

로컬 checkpoint 경로:

```text
models/koelectra-risk-pseudo
```

이 폴더는 `.gitignore` 대상이라 GitHub에는 올라가지 않는다.

## 4. Hugging Face 업로드

데모용 checkpoint는 Hugging Face에 public 모델로 업로드했다.

```text
https://huggingface.co/sallychoe/koelectra-risk-pseudo
```

팀원에게 공유한 백엔드 `.env` 설정:

```env
USE_KOELECTRA_CLASSIFIER=true
KOELECTRA_MODEL_NAME_OR_PATH=sallychoe/koelectra-risk-pseudo
ALLOW_MODEL_DOWNLOAD=true
KOELECTRA_MIN_CONFIDENCE=0.5
```

Hugging Face repo가 public이면 별도 `HF_TOKEN` 없이 다운로드 가능하다. private repo로 유지할 경우 서버 환경에 `HF_TOKEN` 설정이 필요하다.

운영/EC2에서 한 번 모델이 캐시에 받아진 뒤에는 네트워크 의존성을 줄이기 위해 `ALLOW_MODEL_DOWNLOAD=false`로 바꾸고 로컬 경로를 쓰는 방식도 가능하다. 다만 현재 공유 방식은 public Hugging Face repo에서 직접 다운로드하는 방식이다.

## 5. KoELECTRA 관련 환경변수

`app/core/config.py`에 추가된 설정:

```python
USE_KOELECTRA_CLASSIFIER: bool = False
KOELECTRA_MODEL_NAME_OR_PATH: str = "snunlp/KR-ELECTRA-discriminator"
KOELECTRA_DEVICE: int = -1
KOELECTRA_MAX_LENGTH: int = 256
KOELECTRA_MIN_CONFIDENCE: float = 0.5
KOELECTRA_LABEL_MAP: str = "LABEL_0:LOW,LABEL_1:MEDIUM,LABEL_2:HIGH"
```

의미:

- `USE_KOELECTRA_CLASSIFIER`: true일 때 KoELECTRA 예측을 우선 사용
- `KOELECTRA_MODEL_NAME_OR_PATH`: Hugging Face model id 또는 로컬 model directory
- `KOELECTRA_DEVICE`: `-1`이면 CPU, GPU를 쓰려면 CUDA device index
- `KOELECTRA_MAX_LENGTH`: tokenizer max length
- `KOELECTRA_MIN_CONFIDENCE`: 이 값보다 낮으면 기존 규칙 기반 fallback
- `KOELECTRA_LABEL_MAP`: 모델 label을 백엔드 위험도 라벨로 매핑

현재 Hugging Face 모델을 쓰려면 다음처럼 설정한다.

```env
USE_KOELECTRA_CLASSIFIER=true
KOELECTRA_MODEL_NAME_OR_PATH=sallychoe/koelectra-risk-pseudo
ALLOW_MODEL_DOWNLOAD=true
KOELECTRA_MIN_CONFIDENCE=0.5
```

## 6. Pseudo fine-tuning 재실행 방법

로컬에서 다시 데모용 checkpoint를 만들려면 다음 명령을 사용한다.

```powershell
.\.venv\Scripts\python.exe scripts\train_koelectra_pseudo.py --allow-download --cpu --epochs 6 --batch-size 8 --max-length 96 --max-source-rows 0 --max-samples-per-label 45 --log-every 4 --output-dir models\koelectra-risk-pseudo
```

CPU-only 환경에서 실행했으며 시간이 꽤 걸린다. 확인 당시 환경은 다음과 같았다.

```text
torch: 2.11.0+cpu
cuda: False
device_count: 0
```

학습 스크립트는 다음을 수행한다.

1. seed 약관 문장과 규칙 조합 문장을 만든다.
2. 기존 `classify_clause_risk_by_rules()`로 pseudo-label을 붙인다.
3. `snunlp/KR-ELECTRA-discriminator`를 `LOW / MEDIUM / HIGH` 3-class classifier로 fine-tuning한다.
4. `models/koelectra-risk-pseudo`에 checkpoint를 저장한다.
5. `pseudo_training_metadata.json`에 학습 메타데이터를 저장한다.

## 7. Gemini 전환

LLM 설명 생성부도 Claude/Anthropic에서 Gemini API로 전환되어 `main`에 같이 push되었다.

수정 파일:

```text
app/services/llm_explainer.py
app/core/config.py
.env.example
requirements.txt
```

변경 요약:

- `ANTHROPIC_API_KEY` 제거
- `GEMINI_API_KEY` 추가
- `anthropic` dependency 제거
- Gemini `generateContent` REST API 호출로 변경

`.env` 예시:

```env
GEMINI_API_KEY=
```

`GEMINI_API_KEY`가 비어 있으면 LLM 호출 없이 fallback 설명을 생성한다.

## 8. 검증 결과

push 전 검증:

```powershell
.\.venv\Scripts\python.exe -m compileall app scripts tests test_analyze_pipeline.py
```

결과:

```text
통과
```

테스트:

```powershell
$env:USE_KOELECTRA_CLASSIFIER='false'
.\.venv\Scripts\python.exe -m unittest discover tests -v
```

결과:

```text
Ran 15 tests
OK
```

diff check:

```powershell
git diff --check
```

결과:

```text
문제 없음
```

## 9. 현재 Git 상태

`main`은 원격에 push 완료되어 있다.

```text
main == origin/main
```

추가로 포함된 파일:

```text
upload_model.py
```

이 파일은 Hugging Face 업로드용 1회성 스크립트다. 토큰은 포함되어 있지 않다.

GitHub에 push하지 않은 로컬 산출물:

```text
models/koelectra-risk-pseudo/
data_collection/data/processed/koelectra_pseudo_labels.jsonl
```

이들은 `.gitignore` 대상이다. 모델은 Hugging Face에 public으로 올라가 있으므로 백엔드는 model id로 내려받으면 된다.

## 10. 백엔드 서버와 프론트 연동 메모

확인 당시 원격 백엔드는 아래 주소에서 살아 있었다.

```text
http://13.125.208.120:8000
```

확인한 endpoint:

```text
GET /health -> {"status":"ok"}
GET /docs -> Swagger UI
GET /openapi.json -> API schema
```

주의:

- `http://13.125.208.120:8000/docs`는 프론트 화면이 아니라 백엔드 Swagger API 문서다.
- 프론트 화면은 별도 프론트 서버/배포 주소에서 열린다.
- 프론트 repo는 다음으로 공유받았다.

```text
https://github.com/SWU-CapstoneProject1/Frontend.git
```

프론트에서 백엔드 base URL은 다음처럼 잡으면 된다.

```env
VITE_API_BASE_URL=http://13.125.208.120:8000
```

프로젝트가 CRA면:

```env
REACT_APP_API_BASE_URL=http://13.125.208.120:8000
```

현재 백엔드 주요 API:

```text
POST /api/analyze/text
POST /api/analyze/url
POST /api/analyze/file
POST /api/analyze
GET  /api/result/{job_id}
GET  /api/report/{job_id}/pdf
GET  /api/stats
POST /api/bookmark
GET  /api/history
GET  /api/dashboard
```

## 11. 다음 작업 추천

바로 이어서 할 일:

1. EC2/컨테이너 `.env`에 Hugging Face 모델 설정 추가
2. 서버 재시작 후 `/api/analyze/text`로 KoELECTRA 경로가 실제 사용되는지 확인
3. 프론트 repo를 `Backend`와 같은 상위 폴더에 clone
4. 프론트 API base URL을 `http://13.125.208.120:8000`으로 연결
5. 실제 분석 화면에서 `job_id` 반환, polling, 결과 표시 확인

성능 개선을 위해 나중에 해야 할 일:

1. 실제 약관 조항을 `LOW / MEDIUM / HIGH`로 사람이 라벨링한 데이터셋 구축
2. pseudo-label 모델을 human-labeled 모델로 교체
3. 별도 validation/test set으로 성능 측정
4. KoELECTRA confidence threshold 튜닝
5. 규칙 기반 fallback과 모델 예측을 ensemble할지 결정

팀원에게 설명할 때 핵심 문장:

```text
KoELECTRA 연동과 데모용 pseudo fine-tuning은 완료했습니다.
모델은 Hugging Face repo(sallychoe/koelectra-risk-pseudo)에 업로드되어 있고,
백엔드 .env에 USE_KOELECTRA_CLASSIFIER=true와 모델 ID를 넣으면 바로 다운로드해서 사용할 수 있습니다.
다만 현재 checkpoint는 기존 규칙 기반 결과를 pseudo-label로 학습한 데모용이라,
논문/서비스 성능 검증 단계에서는 사람이 라벨링한 데이터로 다시 학습해야 합니다.
```
