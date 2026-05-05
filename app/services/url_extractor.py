"""
URL에서 약관 본문 텍스트 추출
- httpx로 페이지 요청
- BeautifulSoup으로 본문 파싱 (네비게이션·광고 등 제거)
"""
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

# 제거할 태그 (메뉴, 푸터, 광고 등 본문 외 영역)
_REMOVE_TAGS = {
    "script", "style", "noscript", "nav", "header", "footer",
    "aside", "form", "button", "iframe", "svg",
}

# 본문 후보 태그 (우선순위 순)
_CONTENT_CANDIDATES = [
    {"id": re.compile(r"terms|privacy|policy|약관|이용|개인정보", re.I)},
    {"class": re.compile(r"terms|privacy|policy|content|main|body|약관", re.I)},
]

REQUEST_TIMEOUT = 15  # 초
MAX_TEXT_LENGTH = 50_000  # 너무 긴 페이지 자르기


def extract_text_from_url(url: str) -> str:
    """
    URL을 받아 약관 본문 텍스트를 반환.
    실패 시 ValueError 발생.
    """
    html = _fetch_html(url)
    text = _parse_text(html)

    if not text or len(text.strip()) < 50:
        raise ValueError("페이지에서 약관 본문을 추출하지 못했습니다")

    return text[:MAX_TEXT_LENGTH]


def _fetch_html(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    }
    try:
        response = httpx.get(url, headers=headers, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.TimeoutException:
        raise ValueError(f"페이지 요청 시간이 초과되었습니다 ({REQUEST_TIMEOUT}초)")
    except httpx.HTTPStatusError as e:
        raise ValueError(f"페이지를 불러올 수 없습니다 (HTTP {e.response.status_code})")
    except httpx.RequestError:
        raise ValueError("URL에 접근할 수 없습니다. 주소를 확인해주세요")


def _parse_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # 불필요한 태그 제거
    for tag in soup.find_all(_REMOVE_TAGS):
        tag.decompose()

    # 본문 영역 탐색
    content_el = None
    for attrs in _CONTENT_CANDIDATES:
        content_el = soup.find(True, attrs)
        if content_el:
            break

    target = content_el if content_el else soup.find("body") or soup

    # 텍스트 추출 및 정리
    lines = []
    for el in target.descendants:
        if el.name in {"p", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "div", "span"}:
            text = el.get_text(separator=" ", strip=True)
            if text:
                lines.append(text)

    raw = "\n".join(lines)

    # 연속 공백·빈 줄 정리
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip()
