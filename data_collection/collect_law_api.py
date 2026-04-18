import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

LAW_API_KEY = os.getenv("LAW_API_KEY")


def call_law_api():
    url = "http://www.law.go.kr/DRF/lawSearch.do"
    params = {
        "OC": LAW_API_KEY,
        "target": "law",
        "type": "JSON",
        "query": "자동차관리법",
        "display": 5,
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    print("status:", response.status_code)
    print("final url:", response.url)
    print("content-type:", response.headers.get("Content-Type"))
    print(response.text[:1000])

    os.makedirs("data_collection/data/raw", exist_ok=True)

    data = response.json()
    with open("data_collection/data/raw/law_search_sample.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("저장 완료: data_collection/data/raw/law_search_sample.json")


if __name__ == "__main__":
    call_law_api()