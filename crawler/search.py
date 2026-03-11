from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pymorphy3


_WORD_RE = re.compile(r"[A-Za-z\u0400-\u04FF]+(?:-[A-Za-z\u0400-\u04FF]+)*")
_QUERY_TOKEN_RE = re.compile(
    r"\(|\)|\bAND\b|\bOR\b|\bNOT\b|[A-Za-z\u0400-\u04FF]+(?:-[A-Za-z\u0400-\u04FF]+)*",
    re.IGNORECASE,
)
_OPS = {"AND", "OR", "NOT"}
_PRIORITY = {"OR": 1, "AND": 2, "NOT": 3}


def _norm_token(token: str) -> str:
    token = token.replace("\u00a0", " ").strip().lower()
    token = token.replace("–", "-").replace("—", "-")
    token = re.sub(r"\s+", "", token)
    return token


def _parse_lemmas_file(path: Path) -> set[str]:
    terms: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        lemma = line.split(maxsplit=1)[0]
        lemma = _norm_token(lemma)
        if lemma and _WORD_RE.fullmatch(lemma):
            terms.add(lemma)
    return terms


def build_inverted_index(lemmas_dir: Path) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for lemmas_file in sorted(lemmas_dir.glob("*.txt")):
        doc_id = lemmas_file.stem
        for term in _parse_lemmas_file(lemmas_file):
            postings = index.setdefault(term, set())
            postings.add(doc_id)
    return index


def save_inverted_index(index: dict[str, set[str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for term in sorted(index.keys()):
            docs = " ".join(sorted(index[term]))
            f.write(f"{term}\t{docs}\n")


def load_inverted_index(index_path: Path) -> tuple[dict[str, set[str]], set[str]]:
    index: dict[str, set[str]] = {}
    universe: set[str] = set()
    for line in index_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", maxsplit=1)
        term = _norm_token(parts[0])
        docs = set(parts[1].split()) if len(parts) > 1 and parts[1].strip() else set()
        index[term] = docs
        universe.update(docs)
    return index, universe


def load_doc_urls(index_path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in index_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", maxsplit=1)
        if len(parts) != 2:
            continue
        out[parts[0].strip()] = parts[1].strip()
    return out


def _normalize_query_term(term: str, morph: pymorphy3.MorphAnalyzer) -> str:
    token = _norm_token(term)
    if not token:
        return token
    if not _WORD_RE.fullmatch(token):
        return token
    return _norm_token(morph.parse(token)[0].normal_form)


def tokenize_query(query: str, morph: pymorphy3.MorphAnalyzer) -> list[str]:
    tokens: list[str] = []
    pos = 0
    for m in _QUERY_TOKEN_RE.finditer(query):
        if query[pos:m.start()].strip():
            raise ValueError(f"Недопустимый фрагмент запроса: {query[pos:m.start()]!r}")

        raw = m.group(0)
        upper = raw.upper()
        if upper in _OPS or raw in {"(", ")"}:
            tokens.append(upper if upper in _OPS else raw)
        else:
            tokens.append(_normalize_query_term(raw, morph))
        pos = m.end()

    if query[pos:].strip():
        raise ValueError(f"Недопустимый фрагмент запроса: {query[pos:]!r}")
    return tokens


def _to_rpn(tokens: list[str]) -> list[str]:
    output: list[str] = []
    stack: list[str] = []

    for tok in tokens:
        if tok in _OPS:
            while stack and stack[-1] in _OPS and (
                _PRIORITY[stack[-1]] > _PRIORITY[tok]
                or (_PRIORITY[stack[-1]] == _PRIORITY[tok] and tok != "NOT")
            ):
                output.append(stack.pop())
            stack.append(tok)
            continue

        if tok == "(":
            stack.append(tok)
            continue

        if tok == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            if not stack:
                raise ValueError("Несогласованные скобки в запросе")
            stack.pop()
            continue

        output.append(tok)

    while stack:
        top = stack.pop()
        if top in {"(", ")"}:
            raise ValueError("Несогласованные скобки в запросе")
        output.append(top)

    return output


@dataclass
class SearchResult:
    query_tokens: list[str]
    rpn: list[str]
    docs: list[str]


def eval_boolean_query(
    query: str,
    *,
    index: dict[str, set[str]],
    universe: set[str],
    morph: pymorphy3.MorphAnalyzer | None = None,
) -> SearchResult:
    morph = morph or pymorphy3.MorphAnalyzer()
    tokens = tokenize_query(query, morph=morph)
    if not tokens:
        return SearchResult(query_tokens=[], rpn=[], docs=[])

    rpn = _to_rpn(tokens)
    stack: list[set[str]] = []

    for tok in rpn:
        if tok == "NOT":
            if not stack:
                raise ValueError("Оператор NOT не имеет аргумента")
            operand = stack.pop()
            stack.append(universe - operand)
            continue

        if tok in {"AND", "OR"}:
            if len(stack) < 2:
                raise ValueError(f"Оператор {tok} не имеет аргументов")
            right = stack.pop()
            left = stack.pop()
            stack.append(left & right if tok == "AND" else left | right)
            continue

        stack.append(set(index.get(tok, set())))

    if len(stack) != 1:
        raise ValueError("Некорректный булев запрос")

    return SearchResult(query_tokens=tokens, rpn=rpn, docs=sorted(stack.pop()))
