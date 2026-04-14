# collect_ftc_data.py (STABLE FINAL)

import re
import json
import time
import logging
import hashlib
from pathlib import Path
from datetime import datetime

import httpx
import fitz
from bs4 import BeautifulSoup

# ================================
# 설정
# ================================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR  = DATA_DIR / "raw"

RAW_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

CASE_BASE = "https://case.ftc.go.kr/ocp/co/ltfr.do"
CASE_PDF  = "https://case.ftc.go.kr/ocp/common/fileDown.do"
FTC_HOST  = "https://www.ftc.go.kr"

HEADERS = {"User-Agent": "Mozilla/5.0"}

KEYWORDS = ["약관", "불공정약관"]

# ================================
# 텍스트 정제
# ================================
def clean_text(text):
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

# ================================
# 중복 키 생성
# ================================
def make_key(title, date):
    return hashlib.md5((title + date).encode()).hexdigest()

# ================================
# HTML 본문
# ================================
def get_html(client, doc_id):
    if not doc_id:
        return ""

    try:
        r = client.get(
            "https://case.ftc.go.kr/ocp/co/ltfrView.do",
            params={"docId": doc_id}
        )

        soup = BeautifulSoup(r.text, "html.parser")

        for sel in ["div.board_view_con", "td.bdViewCon", "div#content"]:
            el = soup.select_one(sel)
            if el:
                return el.get_text("\n", strip=True)

    except Exception as e:
        log.warning(f"HTML 실패: {e}")

    return ""

# ================================
# PDF 추출
# ================================
def extract_pdf(path):
    try:
        doc = fitz.open(path)
        return "\n".join(p.get_text() for p in doc)
    except:
        return ""

# ================================
# case.ftc 수집
# ================================
def collect_case(seen=None):
    if seen is None:
        seen = set()

    client = httpx.Client(headers=HEADERS, follow_redirects=True)
    results = []

    MAX_PAGES = 200

    for kw in KEYWORDS:
        prev_ids = set()

        for page in range(1, MAX_PAGES + 1):

            r = client.get(CASE_BASE, params={
                "pageIndex": page,
                "searchKrwd": kw
            })

            soup = BeautifulSoup(r.text, "html.parser")
            rows = soup.select("tbody tr")

            if not rows:
                break

            current_ids = set()

            for row in rows:
                inputs = row.find_all("input")

                case_no     = ""
                title       = ""
                date        = ""
                file_id     = ""
                file_sn     = ""
                html_doc_id = ""

                for inp in inputs:
                    name = inp.get("name", "")
                    val  = inp.get("value", "")

                    if name == "csno":
                        case_no = val
                    elif name == "csname":
                        title = val
                    elif name == "apdate":
                        date = val
                    elif name == "fileId":
                        file_id = val
                    elif name == "fileSn":
                        file_sn = val

                    if val.startswith("OCPLTFR"):
                        html_doc_id = val

                if not case_no:
                    continue

                current_ids.add(case_no)

                # 소스 통합 중복 제거
                key = make_key(title, date)
                if key in seen:
                    continue
                seen.add(key)

                # HTML 먼저 시도
                content = get_html(client, html_doc_id)

                # HTML 없으면 PDF 다운로드
                pdf_path = ""
                if not content and file_id:
                    try:
                        pdf_url = f"{CASE_PDF}?fileId={file_id}&fileSn={file_sn}"
                        path = RAW_DIR / f"{case_no}.pdf"

                        res = client.get(pdf_url)

                        if len(res.content) > 1000:
                            path.write_bytes(res.content)
                            pdf_path = str(path)

                    except Exception as e:
                        log.warning(f"PDF 실패: {e}")

                results.append({
                    "case_no":  case_no,
                    "title":    title,
                    "date":     date,
                    "content":  content,
                    "pdf_path": pdf_path,
                })

                time.sleep(0.3)

            # 동일 페이지 반복 방지
            if current_ids == prev_ids:
                log.info("페이지 반복 감지 → 종료")
                break

            prev_ids = current_ids

    return results

# ================================
# ftc.go.kr 수집
# ================================
def collect_ftc(seen=None):
    if seen is None:
        seen = set()

    client = httpx.Client(headers=HEADERS, follow_redirects=True, verify=False)
    results = []

    BASE_URL = "https://www.ftc.go.kr/www/selectBbsNttList.do?bordCd=208&key=208"

    for page in range(1, 10):

        r = client.get(BASE_URL + f"&pageIndex={page}")
        soup = BeautifulSoup(r.text, "html.parser")

        rows = soup.select("tbody tr")

        if not rows:
            break

        for row in rows:
            a = row.find("a")
            if not a:
                continue

            title = a.text.strip()
            url   = FTC_HOST + a["href"]

            # 날짜 추출 시도
            texts = [td.get_text(strip=True) for td in row.find_all("td")]
            date  = next(
                (t for t in texts if re.match(r"\d{4}[.\-]\d{2}", t)), ""
            )

            # 소스 통합 중복 제거
            key = make_key(title, date)
            if key in seen:
                continue
            seen.add(key)

            try:
                d = client.get(url)
                s = BeautifulSoup(d.text, "html.parser")

                content = ""
                for sel in ["div.board_view_con", "td.bdViewCon"]:
                    el = s.select_one(sel)
                    if el:
                        content = el.get_text("\n", strip=True)

                results.append({
                    "title":    title,
                    "content":  content,
                    "date":     date,
                    "pdf_path": "",
                })

            except Exception as e:
                log.warning(f"ftc 상세 실패: {e}")

            time.sleep(0.3)

    return results

# ================================
# 데이터셋 생성
# ================================
def build(records):

    out = DATA_DIR / "decisions.jsonl"
    now = datetime.now().isoformat()

    with open(out, "w", encoding="utf-8") as f:

        for r in records:

            text = r["content"]

            if not text and r.get("pdf_path"):
                text = extract_pdf(r["pdf_path"])

            if not text:
                text = r["title"]

            text = clean_text(text)

            uid = hashlib.md5(text.encode()).hexdigest()[:8]

            f.write(json.dumps({
                "id":           uid,
                "text":         text,
                "title":        r["title"],
                "date":         r["date"],
                "collected_at": now,
            }, ensure_ascii=False) + "\n")

    print("완료:", out)

# ================================
# 실행
# ================================
if __name__ == "__main__":

    seen = set()  # 소스 간 공유

    print("1. case.ftc 수집")
    case_data = collect_case(seen)

    print("2. ftc.go.kr 수집")
    ftc_data = collect_ftc(seen)

    all_data = case_data + ftc_data

    print("3. dataset 생성")
    build(all_data)