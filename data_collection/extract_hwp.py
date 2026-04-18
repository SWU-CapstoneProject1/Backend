"""
표준약관 HWP 파일 텍스트 추출
약간동의(YakganDongui) 프로젝트용

사용법:
    python extract_hwp.py

입력: data_collection/data/standard/ 폴더의 .hwp 파일들
출력: data_collection/data/standard_extracted/ 폴더의 .json 파일들
      data_collection/data/standard_labels.jsonl (라벨링 데이터)
"""

import os
import re
import json
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime

# ================================
# 경로 설정
# ================================
BASE_DIR    = Path(__file__).parent
DATA_DIR    = BASE_DIR / "data"
HWP_DIR     = DATA_DIR / "standard"          # HWP 파일 위치
OUTPUT_DIR  = DATA_DIR / "standard_extracted" # 추출 결과
JSONL_PATH  = DATA_DIR / "standard_labels.jsonl"

HWP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ================================
# HWP 텍스트 추출
# ================================
def extract_hwp(hwp_path: Path) -> str:
    """
    pyhwp Python 모듈로 HWP에서 텍스트 추출
    """
    import sys

    try:
        result = subprocess.run(
            [sys.executable, "-m", "hwp5.hwp5txt", str(hwp_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            print(f"  [경고] hwp5txt 실패: {result.stderr[:200]}")
            return ""
    except subprocess.TimeoutExpired:
        print(f"  [경고] 타임아웃: {hwp_path.name}")
        return ""
    except Exception as e:
        print(f"  [오류] {e}")
        return ""


# ================================
# 텍스트 정제
# ================================
def clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n +", "\n", text)
    return text.strip()


# ================================
# 조항 단위 분리
# ================================
def split_clauses(text: str) -> list[dict]:
    """
    제X조 패턴으로 조항 단위 분리
    """
    pattern = r"(제\s*\d+\s*조(?:\s*의\s*\d+)?\s*[^\n]*)"
    parts   = re.split(pattern, text)

    clauses = []
    for i in range(1, len(parts) - 1, 2):
        heading  = parts[i].strip()
        body     = parts[i + 1].strip() if i + 1 < len(parts) else ""
        combined = f"{heading}\n{body}".strip()

        if len(combined) > 20:
            clauses.append({
                "heading": heading,
                "text":    combined,
            })

    # 조항 패턴이 없으면 문단 단위로 분리
    if not clauses:
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 20]
        clauses = [{"heading": "", "text": p} for p in paragraphs]

    return clauses


# ================================
# 메인 처리
# ================================
def process_all():
    hwp_files = list(HWP_DIR.glob("*.hwp")) + list(HWP_DIR.glob("*.HWP"))

    if not hwp_files:
        print(f"\n[!] HWP 파일이 없어요.")
        print(f"    {HWP_DIR} 폴더에 표준약관 HWP 파일을 넣어주세요.")
        return

    print(f"\n총 {len(hwp_files)}개 HWP 파일 처리 시작")
    print("=" * 50)

    all_labels  = []
    now         = datetime.now().isoformat()
    total_clauses = 0

    for hwp_path in hwp_files:
        print(f"\n처리 중: {hwp_path.name}")

        # 텍스트 추출
        raw_text = extract_hwp(hwp_path)
        if not raw_text:
            print(f"  건너뜀 (텍스트 추출 실패)")
            continue

        # 정제
        clean  = clean_text(raw_text)
        clauses = split_clauses(clean)

        print(f"  조항 수: {len(clauses)}개")
        total_clauses += len(clauses)

        # JSON 저장
        result = {
            "file":         hwp_path.name,
            "full_text":    clean,
            "clause_count": len(clauses),
            "clauses":      clauses,
            "extracted_at": now,
        }
        out_path = OUTPUT_DIR / (hwp_path.stem + ".json")
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # JSONL 라벨 데이터 생성 (표준약관 = safe 라벨)
        for i, clause in enumerate(clauses):
            uid = hashlib.md5(clause["text"].encode()).hexdigest()[:8]
            all_labels.append({
                "id":           f"std_{hwp_path.stem}_{i}",
                "text":         clause["text"],
                "label":        "safe",        # 표준약관 = 정상
                "source":       "표준약관",
                "file":         hwp_path.name,
                "heading":      clause["heading"],
                "collected_at": now,
            })

    # JSONL 저장
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for item in all_labels:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print("\n" + "=" * 50)
    print(f"완료!")
    print(f"  처리된 파일:  {len(hwp_files)}개")
    print(f"  추출된 조항:  {total_clauses}개")
    print(f"  라벨 데이터:  {JSONL_PATH}")
    print(f"  (라벨: safe — 표준약관은 정상 조항)")


if __name__ == "__main__":
    process_all()