import argparse
from pathlib import Path

import pymorphy3

from .downloader import crawl_from_list, build_url_list_from_seeds
from .validators import UrlFilters
from .robots import RobotsCache

from .textproc import TokenizeConfig, build_per_page_files
from .search import (
    build_inverted_index,
    save_inverted_index,
    load_inverted_index,
    load_doc_urls,
    eval_boolean_query,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="crawler",
        description="HW web crawler (download raw HTML pages) + tokenization + lemmatization.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build-list", help="Build urls.txt from seed pages.")
    p_build.add_argument("--seeds", required=True, type=Path, help="Path to seed_pages.txt")
    p_build.add_argument("--out", required=True, type=Path, help="Output urls.txt")
    p_build.add_argument("--max-links", type=int, default=400, help="How many links to collect")
    p_build.add_argument("--same-domain", action="store_true", help="Keep links only from the same domain as seeds")
    p_build.add_argument("--delay", type=float, default=1.0, help="Delay between HTTP requests (seconds)")
    p_build.add_argument("--timeout", type=float, default=15.0, help="Request timeout (seconds)")

    p_crawl = sub.add_parser("crawl", help="Download pages from a prepared list (urls.txt).")
    p_crawl.add_argument("--urls", required=True, type=Path, help="Path to urls.txt (prepared list)")
    p_crawl.add_argument("--out", required=True, type=Path, help="Output folder (will contain pages/, index.txt, logs)")
    p_crawl.add_argument("--limit", type=int, default=100, help="How many pages to successfully download")
    p_crawl.add_argument("--delay", type=float, default=1.0, help="Delay between requests (seconds)")
    p_crawl.add_argument("--timeout", type=float, default=15.0, help="Request timeout (seconds)")
    p_crawl.add_argument("--retries", type=int, default=2, help="Retries on network errors")
    p_crawl.add_argument("--min-bytes", type=int, default=5000, help="Minimal HTML size to accept")
    p_crawl.add_argument("--min-cyr", type=int, default=200, help="Minimal count of Cyrillic letters")
    p_crawl.add_argument("--min-cyr-ratio", type=float, default=0.25, help="Minimal Cyrillic ratio among letters")
    p_crawl.add_argument("--respect-robots", action="store_true", help="Respect robots.txt (recommended)")
    p_crawl.add_argument("--skip-wikipedia", action="store_true", default=True, help="Skip wikipedia.org and wikimedia.org")
    p_crawl.add_argument(
        "--user-agent",
        default="Mozilla/5.0 (compatible; HW-Crawler/1.0; +https://example.com)",
        help="Custom User-Agent",
    )

    p_tp = sub.add_parser("tokens-pages", help="Create per-page tokens/ and lemmas/ txt files from saved HTML pages.")
    p_tp.add_argument("--pages", required=True, type=Path, help="Folder with *.html (e.g. output/pages)")
    p_tp.add_argument("--out", required=True, type=Path, help="Output folder (will create tokens/ and lemmas/ inside)")
    p_tp.add_argument("--limit", type=int, default=102, help="How many html files to process (default 102)")
    p_tp.add_argument("--min-len", type=int, default=2, help="Minimal token length")
    p_tp.add_argument("--max-len", type=int, default=40, help="Max token length")

    p_inv = sub.add_parser("build-inverted", help="Build inverted term index from per-page lemmas/*.txt files.")
    p_inv.add_argument("--lemmas", required=True, type=Path, help="Folder with per-page lemmas files")
    p_inv.add_argument("--out", required=True, type=Path, help="Output file for inverted index")

    p_bs = sub.add_parser("boolean-search", help="Run boolean query over an inverted index.")
    p_bs.add_argument("--index", required=True, type=Path, help="Path to inverted index file")
    p_bs.add_argument("--query", required=True, type=str, help="Query string with AND/OR/NOT and parentheses")
    p_bs.add_argument(
        "--doc-index",
        type=Path,
        default=None,
        help="Optional path to output/index.txt for doc_id -> URL mapping",
    )

    args = parser.parse_args()

    if args.cmd == "build-list":
        build_url_list_from_seeds(
            seeds_path=args.seeds,
            out_path=args.out,
            max_links=args.max_links,
            same_domain=args.same_domain,
            delay=args.delay,
            timeout=args.timeout,
        )
        print(f"[ok] urls saved to: {args.out}")
        return 0

    if args.cmd == "crawl":
        robots = RobotsCache(user_agent=args.user_agent) if args.respect_robots else None

        filters = UrlFilters(
            skip_wikipedia=args.skip_wikipedia,
        )

        crawl_from_list(
            urls_path=args.urls,
            out_dir=args.out,
            limit=args.limit,
            delay=args.delay,
            timeout=args.timeout,
            retries=args.retries,
            user_agent=args.user_agent,
            min_bytes=args.min_bytes,
            min_cyr=args.min_cyr,
            min_cyr_ratio=args.min_cyr_ratio,
            robots=robots,
            filters=filters,
        )
        print(f"[ok] done. Check: {args.out / 'index.txt'} and {args.out / 'pages'}")
        return 0

    if args.cmd == "tokens-pages":
        out_root: Path = args.out
        tokens_dir = out_root / "tokens"
        lemmas_dir = out_root / "lemmas"

        cfg = TokenizeConfig(
            min_len=args.min_len,
            max_len=args.max_len,
            keep_latin=False,
        )

        build_per_page_files(
            args.pages,
            tokens_dir=tokens_dir,
            lemmas_dir=lemmas_dir,
            limit=args.limit,
            cfg=cfg,
        )

        print("[ok] per-page files created:")
        print(f"     tokens: {tokens_dir}")
        print(f"     lemmas: {lemmas_dir}")
        return 0

    if args.cmd == "build-inverted":
        index = build_inverted_index(args.lemmas)
        save_inverted_index(index, args.out)
        print(f"[ok] inverted index saved: {args.out}")
        print(f"     terms: {len(index)}")
        print(f"     docs: {len({doc for docs in index.values() for doc in docs})}")
        return 0

    if args.cmd == "boolean-search":
        index, universe = load_inverted_index(args.index)
        result = eval_boolean_query(
            args.query,
            index=index,
            universe=universe,
            morph=pymorphy3.MorphAnalyzer(),
        )

        print("[ok] query parsed")
        print(f"     tokens: {' '.join(result.query_tokens)}")
        print(f"     rpn: {' '.join(result.rpn)}")
        print(f"     matches: {len(result.docs)}")

        doc_urls = load_doc_urls(args.doc_index) if args.doc_index else {}
        for doc_id in result.docs:
            if doc_id in doc_urls:
                print(f"{doc_id}\t{doc_urls[doc_id]}")
            else:
                print(doc_id)
        return 0

    return 2
