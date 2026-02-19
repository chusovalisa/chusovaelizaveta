import argparse
from pathlib import Path

from .downloader import crawl_from_list
from .validators import UrlFilters
from .robots import RobotsCache
from .downloader import build_url_list_from_seeds


def main() -> int:
    parser = argparse.ArgumentParser(prog="crawler", description="HW web crawler (download raw HTML pages).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build-list", help="Build data/urls.txt from seed pages (optional helper).")
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
    p_crawl.add_argument("--user-agent", default="Mozilla/5.0 (compatible; HW-Crawler/1.0; +https://example.com)",
                         help="Custom User-Agent")

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

    return 2
