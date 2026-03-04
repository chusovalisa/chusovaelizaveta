from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
import re

import pymorphy3
from bs4 import BeautifulSoup


_WORD_RE = re.compile(r"[A-Za-z\u0400-\u04FF]+(?:-[A-Za-z\u0400-\u04FF]+)*")
_BAD_POS = {"CONJ", "PREP", "PRCL", "INTJ", "NUMR"}


@dataclass
class TokenizeConfig:
    min_len: int = 2
    max_len: int = 40
    keep_latin: bool = False


def _norm_token(w: str) -> str:
    w = w.replace("\u00a0", " ").strip().lower()
    w = w.replace("–", "-").replace("—", "-")
    w = re.sub(r"\s+", "", w)
    return w


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def iter_tokens_from_text(text: str, cfg: TokenizeConfig) -> list[str]:
    tokens: list[str] = []
    for m in _WORD_RE.finditer(text):
        w = _norm_token(m.group(0))

        if len(w) < cfg.min_len or len(w) > cfg.max_len:
            continue

        if not cfg.keep_latin:
            if not re.search(r"[\u0400-\u04FF]", w):
                continue

        tokens.append(w)
    return tokens


def process_one_page(
    html_path: Path,
    *,
    cfg: TokenizeConfig,
    morph: pymorphy3.MorphAnalyzer,
) -> tuple[list[str], dict[str, list[str]]]:
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    text = html_to_text(html)

    uniq_tokens: set[str] = set()
    lemma2set: dict[str, set[str]] = defaultdict(set)

    for token in iter_tokens_from_text(text, cfg):
        if any(ch.isdigit() for ch in token):
            continue

        p = morph.parse(token)[0]
        if p.tag.POS in _BAD_POS:
            continue

        lemma = _norm_token(p.normal_form)
        if len(lemma) < cfg.min_len or len(lemma) > cfg.max_len:
            continue

        uniq_tokens.add(token)
        lemma2set[lemma].add(token)

    tokens_sorted = sorted(uniq_tokens)

    lemma2tokens: dict[str, list[str]] = {
        lemma: sorted(toks) for lemma, toks in lemma2set.items()
    }

    return tokens_sorted, lemma2tokens


def write_tokens_file(tokens: list[str], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(t + "\n" for t in tokens), encoding="utf-8")


def write_lemmas_file(lemma2tokens: dict[str, list[str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for lemma in sorted(lemma2tokens.keys()):
        toks = lemma2tokens[lemma]

        toks = sorted(set(toks))

        lines.append(lemma + " " + " ".join(toks) + "\n")

    out_path.write_text("".join(lines), encoding="utf-8")


def build_per_page_files(
    pages_dir: Path,
    *,
    tokens_dir: Path,
    lemmas_dir: Path,
    limit: int | None = None,
    cfg: TokenizeConfig | None = None,
) -> None:
    cfg = cfg or TokenizeConfig()
    morph = pymorphy3.MorphAnalyzer()

    tokens_dir.mkdir(parents=True, exist_ok=True)
    lemmas_dir.mkdir(parents=True, exist_ok=True)

    html_files = sorted(pages_dir.glob("*.html"))
    if limit is not None:
        html_files = html_files[:limit]

    for html_path in html_files:
        stem = html_path.stem
        tokens, lemma2tokens = process_one_page(html_path, cfg=cfg, morph=morph)

        write_tokens_file(tokens, tokens_dir / f"{stem}.txt")
        write_lemmas_file(lemma2tokens, lemmas_dir / f"{stem}.txt")