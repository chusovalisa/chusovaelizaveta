from dataclasses import dataclass
import re
from urllib.parse import urlparse

_CYR_RE = re.compile(r"[\u0400-\u04FF]")
_LETTERS_RE = re.compile(r"[A-Za-z\u0400-\u04FF]")

_BAD_EXT_RE = re.compile(
    r"\.(jpg|jpeg|png|gif|webp|svg|ico|pdf|zip|rar|7z|mp3|mp4|avi|mov|css|js)(\?.*)?$",
    re.IGNORECASE,
)

_FAKE_404_RE = re.compile(r"(?i)<title>\s*404|страниц[аы]\s+не\s+найден|not\s+found")


@dataclass(frozen=True)
class UrlFilters:
    skip_wikipedia: bool = True


def is_http_url(url: str) -> bool:
    try:
        p = urlparse(url.strip())
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def is_disallowed_by_filters(url: str, filters: UrlFilters) -> bool:
    host = urlparse(url).netloc.lower()
    if filters.skip_wikipedia:
        if host.endswith("wikipedia.org") or host.endswith("wikimedia.org"):
            return True
    if _BAD_EXT_RE.search(url):
        return True
    return False


def is_html_content(content_type: str | None) -> bool:
    if not content_type:
        return True
    ct = content_type.lower()
    return ("text/html" in ct) or ("application/xhtml+xml" in ct)


def looks_like_fake_404(html: str) -> bool:
    return bool(_FAKE_404_RE.search(html))


def russian_score(html: str) -> tuple[int, float]:
    cyr = len(_CYR_RE.findall(html))
    letters = len(_LETTERS_RE.findall(html))
    ratio = (cyr / letters) if letters else 0.0
    return cyr, ratio


def is_good_russian_html(html: str, min_bytes: int, min_cyr: int, min_ratio: float) -> tuple[bool, str]:
    if not html:
        return False, "empty_body"
    if len(html.encode("utf-8", errors="ignore")) < min_bytes:
        return False, f"too_small<{min_bytes}"
    if looks_like_fake_404(html):
        return False, "looks_like_404_page"
    cyr, ratio = russian_score(html)
    if cyr < min_cyr:
        return False, f"too_few_cyrillic<{min_cyr}"
    if ratio < min_ratio:
        return False, f"cyrillic_ratio<{min_ratio}"
    return True, "ok"
