from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import urljoin, urldefrag, urlparse
import re

import requests
from tqdm import tqdm

from .validators import (
    is_http_url,
    is_disallowed_by_filters,
    is_html_content,
    is_good_russian_html,
    UrlFilters,
)
from .storage import Storage
from .robots import RobotsCache


_LINK_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"file not found: {path}")
    lines = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def _normalize_url(base: str, href: str) -> str | None:
    href = href.strip()
    if not href or href.startswith("mailto:") or href.startswith("tel:") or href.startswith("javascript:"):
        return None
    u = urljoin(base, href)
    u, _ = urldefrag(u)
    return u


def fetch_html(url: str, *, timeout: float, retries: int, user_agent: str) -> tuple[int | None, str | None, str | None, str]:
    """
    Returns: (status_code, content_type, html_text, final_url)
    """
    headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"}
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            status = r.status_code
            ct = r.headers.get("Content-Type")
            html = r.text or ""
            return status, ct, html, str(r.url)
        except requests.RequestException as e:
            last_err = str(e)
            time.sleep(0.6 * (attempt + 1))
    return None, None, None, url if last_err is None else url


def crawl_from_list(
    *,
    urls_path: Path,
    out_dir: Path,
    limit: int,
    delay: float,
    timeout: float,
    retries: int,
    user_agent: str,
    min_bytes: int,
    min_cyr: int,
    min_cyr_ratio: float,
    robots: RobotsCache | None,
    filters: UrlFilters,
):
    urls = _read_lines(urls_path)

    storage = Storage(out_dir)

    seen = set()
    saved_num = 0

    for raw_url in tqdm(urls, desc="Downloading", unit="url"):
        if saved_num >= limit:
            break

        url = raw_url.strip()
        storage.stats.requested += 1

        if not is_http_url(url):
            storage.log_skip(url, "not_http_url")
            continue

        if is_disallowed_by_filters(url, filters):
            storage.log_skip(url, "disallowed_by_filters")
            continue

        if url in seen:
            storage.log_skip(url, "duplicate_url")
            continue
        seen.add(url)

        if robots is not None and not robots.allowed(url):
            storage.log_skip(url, "robots_disallow")
            continue

        status, ct, html, final_url = fetch_html(url, timeout=timeout, retries=retries, user_agent=user_agent)

        time.sleep(max(0.0, delay))

        if status is None:
            storage.log_fail(url, "network_error")
            continue

        if status == 404:
            storage.log_skip(final_url, "http_404")
            continue

        if status < 200 or status >= 300:
            storage.log_skip(final_url, f"http_{status}")
            continue

        if not is_html_content(ct):
            storage.log_skip(final_url, f"not_html_content_type:{ct}")
            continue

        ok, reason = is_good_russian_html(html or "", min_bytes=min_bytes, min_cyr=min_cyr, min_ratio=min_cyr_ratio)
        if not ok:
            storage.log_skip(final_url, reason)
            continue

        saved_num += 1
        storage.save_page(saved_num, final_url, html or "")

    storage.finalize()


def build_url_list_from_seeds(
    *,
    seeds_path: Path,
    out_path: Path,
    max_links: int,
    same_domain: bool,
    delay: float,
    timeout: float,
):
    seeds = _read_lines(seeds_path)
    collected: list[str] = []
    seen: set[str] = set()

    seed_domains = {urlparse(s).netloc.lower() for s in seeds if is_http_url(s)}

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; HW-Crawler/1.0; +https://example.com)",
        "Accept": "text/html,application/xhtml+xml",
    }

    for seed in tqdm(seeds, desc="Scanning seeds", unit="seed"):
        if len(collected) >= max_links:
            break

        if not is_http_url(seed):
            continue

        try:
            r = requests.get(seed, headers=headers, timeout=timeout, allow_redirects=True)
            if r.status_code != 200:
                time.sleep(max(0.0, delay))
                continue
            html = r.text or ""
        except requests.RequestException:
            time.sleep(max(0.0, delay))
            continue

        base = str(r.url)
        for m in _LINK_RE.finditer(html):
            href = m.group(1)
            u = _normalize_url(base, href)
            if not u or not is_http_url(u):
                continue

            if same_domain:
                if urlparse(u).netloc.lower() not in seed_domains:
                    continue

            if re.search(r"\.(jpg|jpeg|png|gif|webp|svg|ico|pdf|zip|rar|7z|css|js)(\?.*)?$", u, re.I):
                continue

            if u in seen:
                continue

            seen.add(u)
            collected.append(u)
            if len(collected) >= max_links:
                break

        time.sleep(max(0.0, delay))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(collected) + "\n", encoding="utf-8")
